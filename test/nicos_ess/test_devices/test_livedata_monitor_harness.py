"""Tests for LiveDataMonitor, which reads the esslivedata heartbeats."""

import threading
import time
from types import SimpleNamespace

import pytest

pytest.importorskip("streaming_data_types")


from nicos.core import status
from nicos_ess.devices.datasources import livedata_monitor
from test.nicos_ess.test_devices.doubles import StubKafkaConsumer
from test.nicos_ess.test_devices.doubles.livedata_messages import (
    VIEW,
    heartbeat,
    job,
    service,
    wait_for,
)


@pytest.fixture
def consumer(monkeypatch):
    stub = StubKafkaConsumer()
    queued = threading.Event()
    queue_record, poll = stub.queue_record, stub.poll

    def queue_and_wake(payload):
        queue_record(payload)
        queued.set()

    # The real consumer blocks for up to timeout_ms when nothing is queued, so
    # the follower does not spin at full speed.
    def blocking_poll(timeout_ms=0):
        record = poll()
        if record is None:
            queued.wait(timeout_ms / 1000)
            queued.clear()
        return record

    stub.queue_record, stub.poll = queue_and_wake, blocking_poll
    monkeypatch.setattr(livedata_monitor.KafkaConsumer, "create", lambda *a, **k: stub)
    return stub


@pytest.fixture
def monitor(daemon_device_harness, consumer):
    device = daemon_device_harness.create_master(
        livedata_monitor.LiveDataMonitor,
        name="livedata_monitor",
        brokers=["localhost:9092"],
        instrument="bifrost",
    )
    yield device
    device.shutdown()


def test_without_heartbeats_the_monitor_warns(monitor):
    assert monitor.read(0) == 0
    assert monitor.status(0) == (status.WARN, "no heartbeat from esslivedata")


def test_a_service_without_jobs_is_ok(monitor, consumer):
    consumer.queue_record(service("monitor_data", "w1"))
    assert wait_for(lambda: monitor.status(0) == (status.OK, "no jobs running"))
    assert monitor.read(0) == 0


def test_the_worst_job_decides_the_status(monitor, consumer):
    consumer.queue_record(service("monitor_data", "w1"))
    consumer.queue_record(job("psc_monitor"))
    consumer.queue_record(job("unified_detector", "error", 240, "no geometry"))

    assert wait_for(lambda: len(monitor.jobs) == 2)
    assert monitor.read(0) == 2
    assert monitor.status(0) == (
        status.ERROR,
        f"{VIEW} on unified_detector: no geometry",
    )


def test_a_stopped_job_is_removed(monitor, consumer):
    consumer.queue_record(service("monitor_data", "w1"))
    consumer.queue_record(job("psc_monitor"))
    consumer.queue_record(job("unified_detector", "error", 240, "no geometry"))
    assert wait_for(lambda: len(monitor.jobs) == 2)

    consumer.queue_record(job("unified_detector", "stopped"))
    assert wait_for(lambda: len(monitor.jobs) == 1)
    assert monitor.read(0) == 1
    assert monitor.status(0) == (status.OK, "1 jobs running")


def test_services_and_a_failing_one(monitor, consumer):
    consumer.queue_record(service("monitor_data", "w1"))
    consumer.queue_record(service("monitor_data", "w2"))
    consumer.queue_record(service("detector_data", "w3", "error", "out of memory"))

    assert wait_for(lambda: len(monitor.services) == 2)
    assert monitor.services["monitor_data"]["workers"] == 2
    assert monitor.status(0) == (
        status.ERROR,
        "esslivedata service detector_data: out of memory",
    )


def test_a_silent_service_is_lost_until_heard_again(monitor, consumer, monkeypatch):
    consumer.queue_record(service("detector_data", "w1"))
    assert wait_for(lambda: monitor.services)
    # Only the monitor sees a clock that runs 10 s ahead, so the heartbeat of
    # w1 has expired while the test keeps the real clock.
    ahead = SimpleNamespace(monotonic=lambda: time.monotonic() + 10, time=time.time)
    monkeypatch.setattr(livedata_monitor, "time", ahead)

    assert wait_for(
        lambda: (
            monitor.status(0)
            == (status.WARN, "no heartbeat from esslivedata detector_data")
        )
    )
    # the restarted service has a new worker
    consumer.queue_record(service("detector_data", "w2"))
    assert wait_for(lambda: monitor.status(0) == (status.OK, "no jobs running"))
    assert monitor.services["detector_data"]["workers"] == 1


def test_a_job_lives_three_of_its_heartbeat_intervals(monitor, consumer, monkeypatch):
    consumer.queue_record(job("psc_monitor", interval=4000))
    assert wait_for(lambda: monitor.jobs)
    ahead = SimpleNamespace(monotonic=lambda: time.monotonic() + 9, time=time.time)
    monkeypatch.setattr(livedata_monitor, "time", ahead)

    # The first job expires after 12 s, so it is still there when the second
    # one is published.
    consumer.queue_record(job("unified_detector"))
    assert wait_for(lambda: len(monitor.jobs) == 2)


def test_the_follower_survives_a_failing_poll(monitor, consumer, caplog):
    poll = consumer.poll
    failures = []

    def fail_twice(*args, **kwargs):
        if len(failures) < 2:
            failures.append(1)
            raise RuntimeError("broker gone")
        return poll(*args, **kwargs)

    consumer.poll = fail_twice
    assert wait_for(lambda: len(failures) == 2)
    consumer.queue_record(job("psc_monitor"))

    assert wait_for(lambda: monitor.jobs)
    assert caplog.text.count("following esslivedata failed") == 1


def test_unreadable_messages_are_skipped_with_one_warning(monitor, consumer, caplog):
    # The job heartbeat has no source name and no job number.
    bad = dict(message_type="job", state="active", job_id={})
    for _ in range(3):
        consumer.queue_record(heartbeat(bad))
    consumer.queue_record(job("psc_monitor"))

    assert wait_for(lambda: monitor.jobs)
    warned = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warned) == 1
