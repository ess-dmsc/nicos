"""Helpers for the NICOS smoke stack test."""

from __future__ import annotations

import math
import time
from textwrap import dedent


def _read_counters(smoke_client) -> dict[str, int]:
    counters_file = smoke_client.runtime_root / "data" / "counters"
    counters: dict[str, int] = {}
    if not counters_file.exists():
        return counters
    for line in counters_file.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        key, value = parts
        counters[key] = int(value)
    return counters


def _wait_for_counter_increment(
    smoke_client, scan_before: int, file_before: int, timeout: float = 10.0
) -> dict[str, int]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        counters = _read_counters(smoke_client)
        if (
            counters.get("scan", 0) >= scan_before + 1
            and counters.get("file", 0) >= file_before + 1
        ):
            return counters
        time.sleep(0.1)
    raise AssertionError(
        "counter increments not observed in time: "
        f"before(scan={scan_before}, file={file_before}) "
        f"after={_read_counters(smoke_client)}"
    )


def _wait_for_moveable_readback(
    smoke_client, moveable, target: float, timeout: float = 15.0
) -> float:
    deadline = time.monotonic() + timeout
    value = float(smoke_client.read(moveable, 0))
    while time.monotonic() < deadline:
        value = float(smoke_client.read(moveable, 0))
        if math.isclose(value, target, abs_tol=0.05):
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


def _filewriter_jobs(smoke_client):
    return smoke_client.eval(
        "["
        "(job.job_id, job.job_number, job.get_state_string(), "
        "job.stop_requested, job.error_msg, job.service_id) "
        "for job in FileWriterStatus._jobs_in_order.values()"
        "]",
        default=[],
    )


def _wait_for_filewriter_job_state(
    smoke_client, job_id: str, expected_state: str, timeout: float = 20.0
):
    deadline = time.monotonic() + timeout
    jobs = []
    while time.monotonic() < deadline:
        jobs = _filewriter_jobs(smoke_client)
        for job in jobs:
            if job[0] == job_id and job[2] == expected_state:
                return job
        time.sleep(0.1)
    raise AssertionError(
        "filewriter job state not observed in time: "
        f"job_id={job_id!r} expected={expected_state!r} jobs={jobs!r}"
    )


def _run_scan_with_filewriter_context(
    smoke_client, *, title: str, timeout: float = 180.0
):
    smoke_client.execute(
        dedent(
            f"""
            __smoke_filewriter_jobs_before = [
                (job.job_id, job.job_number, job.get_state_string())
                for job in FileWriterStatus._jobs_in_order.values()
            ]
            __smoke_jobs_before = FileWriterControl.get_active_jobs()
            with nexusfile_open({title!r}):
                __smoke_jobs_during = FileWriterControl.get_active_jobs()
                __smoke_filewriter_state_during = ""
                __smoke_filewriter_service_during = ""
                import time as __smoke_time
                __smoke_deadline = __smoke_time.monotonic() + 20
                while __smoke_time.monotonic() < __smoke_deadline:
                    __smoke_filewriter_jobs_during = [
                        (
                            job.job_id,
                            job.job_number,
                            job.get_state_string(),
                            job.service_id,
                        )
                        for job in FileWriterStatus._jobs_in_order.values()
                    ]
                    if __smoke_filewriter_jobs_during:
                        __smoke_latest_filewriter = (
                            __smoke_filewriter_jobs_during[-1]
                        )
                        __smoke_filewriter_state_during = (
                            __smoke_latest_filewriter[2]
                        )
                        __smoke_filewriter_service_during = (
                            __smoke_latest_filewriter[3]
                        )
                    if __smoke_filewriter_state_during == "STARTED":
                        break
                    __smoke_time.sleep(0.1)
                scan(SmokeBasicMoveable, [0, 5, 10], timer=2.0)
            __smoke_jobs_after = FileWriterControl.get_active_jobs()
            __smoke_filewriter_jobs_after = [
                (
                    job.job_id,
                    job.job_number,
                    job.get_state_string(),
                    job.stop_requested,
                    job.error_msg,
                    job.service_id,
                )
                for job in FileWriterStatus._jobs_in_order.values()
            ]
            """
        ),
        timeout=timeout,
    )
    return {
        "jobs_before": smoke_client.eval("__smoke_jobs_before", default=[]),
        "jobs_during": smoke_client.eval("__smoke_jobs_during", default=[]),
        "jobs_after": smoke_client.eval("__smoke_jobs_after", default=[]),
        "filewriter_jobs_before": smoke_client.eval(
            "__smoke_filewriter_jobs_before", default=[]
        ),
        "filewriter_state_during": smoke_client.eval(
            "__smoke_filewriter_state_during", default=""
        ),
        "filewriter_service_during": smoke_client.eval(
            "__smoke_filewriter_service_during", default=""
        ),
        "filewriter_jobs_after": smoke_client.eval(
            "__smoke_filewriter_jobs_after", default=[]
        ),
    }
