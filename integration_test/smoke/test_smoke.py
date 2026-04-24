import math

from integration_test.smoke.helpers import (
    _filewriter_jobs,
    _read_counters,
    _run_scan_with_filewriter_context,
    _wait_for_counter_increment,
    _wait_for_filewriter_job_state,
    _wait_for_moveable_readback,
)


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

    counters_before = _read_counters(smoke_client)
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
    assert not _filewriter_jobs(smoke_client)

    filewriter_scan = _run_scan_with_filewriter_context(
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
    job_after_stop = _wait_for_filewriter_job_state(
        smoke_client, job_id, "WRITTEN", timeout=20.0
    )
    assert job_after_stop[3] is True
    assert not job_after_stop[4]
    assert job_after_stop[5] == "nicos-smoke-filewriter-double"
    smoke_client.execute("list_filewriting_jobs()", timeout=30)

    end = _wait_for_moveable_readback(smoke_client, moveable, target=10.0)
    assert math.isclose(end, 10.0, abs_tol=0.05)

    counters_after = _wait_for_counter_increment(smoke_client, scan_before, file_before)
    assert counters_after.get("scan", 0) >= scan_before + 1
    assert counters_after.get("file", 0) >= file_before + 1

    lastscan = int(smoke_client.eval("session.experiment.lastscan", default=0))
    run_number = int(
        smoke_client.eval("session.experiment.get_current_run_number()", default=0)
    )
    assert lastscan >= scan_before + 1
    assert run_number >= file_before + 1
    assert status("FileWriterStatus", 0) is not None
