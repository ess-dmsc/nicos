import math

from integration_test.smoke.helpers import (
    filewriter_jobs,
    last_start_structure,
    read_counters,
    run_scan_with_filewriter_context,
    scan_log_messages,
    wait_for_counter_increment,
    wait_for_filewriter_job_state,
    wait_for_moveable_readback,
)
from integration_test.smoke.run_smoke_stack import SMOKE_FILEWRITER_POOL_TOPIC

SCAN_LOG_TOPIC = "test_smoke_nicos_devices"


def test_full_experiment_workflow_with_filewriter_scan(smoke_client) -> None:
    NewSetup = smoke_client.NewSetup
    NewExperiment = smoke_client.NewExperiment
    NewSample = smoke_client.NewSample
    SetDetectors = smoke_client.SetDetectors
    read = smoke_client.read
    status = smoke_client.status

    readable = smoke_client.dev("SmokeBasicReadable")
    moveable = smoke_client.dev("SmokeBasicMoveable")

    NewSetup("system", "epics_basic", "detector", timeout=90)
    setup_devices = smoke_client.eval(
        "sorted(session._setup_info['epics_basic']['devices'])"
    )
    assert {"SmokeBasicMoveable", "SmokeBasicReadable"} <= set(setup_devices)

    assert status(readable, 0) is not None
    assert status(moveable, 0) is not None
    assert math.isclose(float(read(readable, 0)), 1.23, abs_tol=1e-6)

    counters_before = read_counters(smoke_client)
    scan_before = counters_before.get("scan", 0)
    file_before = counters_before.get("file", 0)

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
    assert not filewriter_jobs(smoke_client)

    filewriter_scan = run_scan_with_filewriter_context(
        smoke_client,
        title="Scan title",
    )
    jobs_before = filewriter_scan["jobs_before"]
    jobs_during = filewriter_scan["jobs_during"]
    jobs_after = filewriter_scan["jobs_after"]

    assert not jobs_before
    assert jobs_during
    assert not jobs_after
    assert not filewriter_scan["filewriter_jobs_before"]
    assert filewriter_scan["filewriter_state_during"] == "STARTED"
    assert filewriter_scan["filewriter_service_during"] == (
        "nicos-smoke-filewriter-double"
    )

    job_id = next(iter(jobs_during))
    job_after_stop = wait_for_filewriter_job_state(
        smoke_client, job_id, "WRITTEN", timeout=20.0
    )
    assert job_after_stop[3] is True
    assert not job_after_stop[4]
    assert job_after_stop[5] == "nicos-smoke-filewriter-double"
    smoke_client.execute("list_filewriting_jobs()", timeout=30)

    end = wait_for_moveable_readback(smoke_client, moveable, target=10.0)
    assert math.isclose(end, 10.0, abs_tol=0.05)

    counters_after = wait_for_counter_increment(smoke_client, scan_before, file_before)
    assert counters_after.get("scan", 0) >= scan_before + 1
    assert counters_after.get("file", 0) >= file_before + 1

    lastscan = int(smoke_client.eval("session.experiment.lastscan", default=0))
    run_number = int(
        smoke_client.eval("session.experiment.get_current_run_number()", default=0)
    )
    assert lastscan >= scan_before + 1
    assert run_number >= file_before + 1
    assert status("FileWriterStatus", 0) is not None

    lastpoint = int(smoke_client.eval("session.experiment.lastpoint", default=0))
    assert counters_after.get("point", 0) == lastpoint
    scan_log = scan_log_messages(smoke_client, SCAN_LOG_TOPIC)
    scans = scan_log["scanlog/scan"][-2:]
    points = scan_log["scanlog/point"][-6:]
    assert [value for value, _ in scans] == [lastscan, 0]
    assert [value for value, _ in points] == [
        lastpoint - 2,
        0,
        lastpoint - 1,
        0,
        lastpoint,
        0,
    ]
    point_times = [timestamp for _, timestamp in points]
    assert point_times == sorted(point_times)
    assert scans[0][1] <= point_times[0]
    assert point_times[-1] <= scans[1][1]
    # Each point counts for the scan's timer=2.0.
    for start, end in zip(point_times[::2], point_times[1::2], strict=True):
        assert 1.5e9 < end - start < 10e9

    structure = last_start_structure(smoke_client, SMOKE_FILEWRITER_POOL_TOPIC)
    entry = structure["children"][0]
    (scan_log_group,) = [
        child for child in entry["children"] if child.get("name") == "scan_log"
    ]
    assert {
        log["name"]: log["children"][0]["config"] for log in scan_log_group["children"]
    } == {
        settype: {
            "source": f"scanlog/{settype}",
            "topic": SCAN_LOG_TOPIC,
            "dtype": "int64",
            "value_units": "",
        }
        for settype in ("scan", "point")
    }
