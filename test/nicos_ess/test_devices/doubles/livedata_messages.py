"""Test doubles that build esslivedata heartbeats as Kafka messages, and a wait helper."""

import json
import time

from streaming_data_types.status_x5f2 import serialise_x5f2

from test.nicos_ess.test_devices.doubles import StubKafkaMessage

VIEW = "bifrost/unified_detector_view/1"


def heartbeat(message, nicos_status=200, interval=1000):
    """Return a heartbeat that says it comes every *interval* ms."""
    raw = serialise_x5f2(
        software_name="livedata",
        software_version="0",
        service_id="",
        host_name="",
        process_id=0,
        update_interval=interval,
        status_json=json.dumps({"status": nicos_status, "message": message}),
    )
    return StubKafkaMessage(raw, topic="bifrost_livedata_heartbeat")


def job(source, state="active", nicos_status=200, error=None, interval=1000):
    return heartbeat(
        dict(
            message_type="job",
            state=state,
            error=error,
            job_id=dict(source_name=source, job_number="1"),
            workflow_id=VIEW,
        ),
        nicos_status,
        interval,
    )


def service(name, worker, state="running", error=None):
    return heartbeat(
        dict(
            message_type="service",
            service_name=name,
            worker_id=worker,
            state=state,
            active_job_count=1,
            error=error,
        )
    )


def wait_for(predicate, timeout=4.0):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True
