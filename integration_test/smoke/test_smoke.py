"""Integration smoke test for a full EPICS + filewriter workflow."""

from __future__ import annotations

import time
from pathlib import Path
from textwrap import dedent

COUNTERS_FILE = Path(__file__).resolve().parents[1] / "runtime" / "data" / "counters"


def _read_counters() -> dict[str, int]:
    counters: dict[str, int] = {}
    if not COUNTERS_FILE.exists():
        return counters
    for line in COUNTERS_FILE.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        key, value = parts
        counters[key] = int(value)
    return counters


def _wait_for_counter_increment(
    scan_before: int, file_before: int, timeout: float = 10.0
) -> dict[str, int]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        counters = _read_counters()
        if (
            counters.get("scan", 0) >= scan_before + 1
            and counters.get("file", 0) >= file_before + 1
        ):
            return counters
        time.sleep(0.1)
    raise AssertionError(
        "counter increments not observed in time: "
        f"before(scan={scan_before}, file={file_before}) "
        f"after={_read_counters()}"
    )


def _wait_for_moveable_readback(
    smoke_client, moveable, target: float, timeout: float = 15.0
) -> float:
    deadline = time.monotonic() + timeout
    value = float(smoke_client.read(moveable, 0))
    while time.monotonic() < deadline:
        value = float(smoke_client.read(moveable, 0))
        if abs(value - target) <= 0.05:
            return value
        time.sleep(0.1)
    move_name = moveable.name
    pv_val = smoke_client.eval(
        f"{move_name}._epics_wrapper.get_pv_value('TEST:SMOKE:MOVE.VAL')",
        default=None,
    )
    pv_rbv = smoke_client.eval(
        f"{move_name}._epics_wrapper.get_pv_value('TEST:SMOKE:MOVE.RBV')",
        default=None,
    )
    raise AssertionError(
        "readback did not reach target in time: "
        f"final={value} target={target} pv_val={pv_val} pv_rbv={pv_rbv}"
    )


def _run_scan_with_filewriter_context(
    smoke_client, *, title: str, timeout: float = 180.0
):
    smoke_client.execute(
        dedent(
            f"""
            __smoke_jobs_before = FileWriterControl.get_active_jobs()
            with nexusfile_open({title!r}):
                __smoke_jobs_during = FileWriterControl.get_active_jobs()
                scan(SmokeBasicMoveable, [0, 5, 10], timer=2.0)
            __smoke_jobs_after = FileWriterControl.get_active_jobs()
            """
        ),
        timeout=timeout,
    )
    jobs_before = smoke_client.eval("__smoke_jobs_before", default=[])
    jobs_during = smoke_client.eval("__smoke_jobs_during", default=[])
    jobs_after = smoke_client.eval("__smoke_jobs_after", default=[])
    return jobs_before, jobs_during, jobs_after


def test_full_experiment_workflow_with_filewriter_scan(smoke_client) -> None:
    """Run one end-to-end experiment workflow with checks at each stage."""
    NewSetup = smoke_client.NewSetup
    NewExperiment = smoke_client.NewExperiment
    NewSample = smoke_client.NewSample
    SetDetectors = smoke_client.SetDetectors
    read = smoke_client.read
    status = smoke_client.status

    readable = smoke_client.dev("SmokeBasicReadable")
    moveable = smoke_client.dev("SmokeBasicMoveable")

    # 1) Setup loading and basic device readiness.
    NewSetup("system", "epics_basic", "detector", timeout=90)
    setup_devices = smoke_client.eval(
        "sorted(session._setup_info['epics_basic']['devices'])"
    )
    assert setup_devices == ["SmokeBasicMoveable", "SmokeBasicReadable"]

    assert status(readable, 0) is not None
    assert status(moveable, 0) is not None
    assert abs(float(read(readable, 0)) - 1.23) <= 1e-6

    counters_before = _read_counters()
    scan_before = counters_before.get("scan", 0)
    file_before = counters_before.get("file", 0)

    # 2) Experiment metadata and sample selection.
    NewExperiment(
        1234,
        "smoke run",
        [{"name": "smoke contact"}],
        [{"name": "smoke user"}],
        timeout=90,
    )
    NewSample("smoke-sample", timeout=60)
    SetDetectors("det", timeout=90)

    assert smoke_client.eval("session.experiment.proposal", default="") == "1234"
    assert smoke_client.read("Sample", 0) == "smoke-sample"
    assert "det" in smoke_client.eval("session.experiment.detlist", default=[])

    # 3) Real daemon-side filewriter context + scan command.
    jobs_before, jobs_during, jobs_after = _run_scan_with_filewriter_context(
        smoke_client,
        title="Scan title",
    )

    assert not jobs_before
    assert jobs_during
    assert not jobs_after

    # 4) Scan outcome and counter accounting checks.
    end = _wait_for_moveable_readback(smoke_client, moveable, target=10.0)
    assert abs(end - 10.0) <= 0.05

    counters_after = _wait_for_counter_increment(scan_before, file_before)
    assert counters_after.get("scan", 0) == scan_before + 1
    assert counters_after.get("file", 0) == file_before + 1

    lastscan = int(smoke_client.eval("session.experiment.lastscan", default=0))
    run_number = int(
        smoke_client.eval("session.experiment.get_current_run_number()", default=0)
    )
    assert lastscan == counters_after.get("scan", 0)
    assert run_number == counters_after.get("file", 0)
    assert status("FileWriterStatus", 0) is not None
