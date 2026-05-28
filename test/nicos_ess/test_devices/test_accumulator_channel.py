import threading
import time

import pytest

pytest.importorskip("streaming_data_types")

from streaming_data_types.alarm_al00 import Severity, serialise_al00
from streaming_data_types.epics_connection_ep01 import ConnectionInfo, serialise_ep01
from streaming_data_types.logdata_f144 import serialise_f144

from nicos.commands.measure import count
from nicos.core import status
from nicos.devices.generic import Detector
from nicos_ess.devices.kafka import readback
from test.nicos_ess.command_helpers import loaded_setup, set_detectors, wait_until
from test.nicos_ess.test_devices.doubles import StubKafkaSubscriber

session_setup = None

TOPIC = "readbacks"
SOURCE = "pulse_source"
CHANNEL = "proton_acc"


@pytest.fixture
def kafka_readback_stubs(monkeypatch):
    subscribers = []

    def create_subscriber(*args, **kwargs):
        subscriber = StubKafkaSubscriber(*args, **kwargs)
        subscribers.append(subscriber)
        return subscriber

    # Kafka is external I/O; route subscriber creation to the in-memory double.
    monkeypatch.setattr(readback, "KafkaSubscriber", create_subscriber)
    return subscribers


def create_accumulator_pair(harness, channel_type="monitor"):
    harness.create_pair(
        readback.KafkaReadbackRouter,
        name="KafkaReadbacks",
        shared={
            "brokers": ["localhost:9092"],
            "topics": [TOPIC],
        },
    )
    config = {
        "kafka": "KafkaReadbacks",
        "topic": TOPIC,
        "source_name": SOURCE,
        "unit": "uC",
        "fmtstr": "%.3f",
    }
    if channel_type is not None:
        config["type"] = channel_type
    return harness.create_pair(
        readback.KafkaAccumulatorChannel, name=CHANNEL, shared=config
    )


@pytest.fixture
def accumulator_pair(device_harness, kafka_readback_stubs):
    return create_accumulator_pair(device_harness)


@pytest.fixture
def daemon_accumulator(accumulator_pair):
    daemon_channel, _poller_channel = accumulator_pair
    return daemon_channel


@pytest.fixture
def poller_accumulator(accumulator_pair):
    _daemon_channel, poller_channel = accumulator_pair
    return poller_channel


@pytest.fixture
def detector_pair(device_harness, accumulator_pair):
    return device_harness.create_pair(
        Detector, name="detector", shared={"monitors": [CHANNEL]}
    )


@pytest.fixture
def daemon_detector(detector_pair):
    daemon_detector_, _poller_detector = detector_pair
    return daemon_detector_


def emit_payload(harness, subscribers, payload):
    harness.run_daemon(subscribers[0].emit_messages, [((0, 0), payload)])


def publish_payload(subscribers, payload):
    subscribers[0].emit_messages([((0, 0), payload)])


def emit_value(harness, subscribers, value, timestamp):
    payload = serialise_f144(SOURCE, value, int(timestamp * 1_000_000_000))
    emit_payload(harness, subscribers, payload)


def publish_value(subscribers, value, timestamp):
    payload = serialise_f144(SOURCE, value, int(timestamp * 1_000_000_000))
    publish_payload(subscribers, payload)


def emit_alarm(
    harness,
    subscribers,
    timestamp,
    severity=Severity.MINOR,
    message="drift",
):
    payload = serialise_al00(
        SOURCE,
        int(timestamp * 1_000_000_000),
        severity,
        message,
    )
    emit_payload(harness, subscribers, payload)


def emit_connection(
    harness,
    subscribers,
    timestamp,
    connection=ConnectionInfo.CONNECTED,
    service="svc",
):
    payload = serialise_ep01(
        int(timestamp * 1_000_000_000),
        connection,
        SOURCE,
        service,
    )
    emit_payload(harness, subscribers, payload)


def emit_deltas(harness, subscribers, values):
    timestamp = time.time()
    for index, value in enumerate(values):
        emit_value(harness, subscribers, value, timestamp + index * 0.001)


def publish_deltas(subscribers, values):
    timestamp = time.time()
    for index, value in enumerate(values):
        publish_value(subscribers, value, timestamp + index * 0.001)


def test_value_info_is_single_monitor_scalar(
    daemon_accumulator, poller_accumulator
):
    for channel in (daemon_accumulator, poller_accumulator):
        info = channel.valueInfo()[0]
        assert (info.name, info.unit, info.type, info.fmtstr) == (
            CHANNEL,
            "uC",
            "monitor",
            "%.3f",
        )


def test_value_info_uses_configured_channel_type(
    device_harness,
    kafka_readback_stubs,
):
    daemon_channel, poller_channel = create_accumulator_pair(
        device_harness, channel_type="counter"
    )
    assert daemon_channel.valueInfo()[0].type == "counter"
    assert poller_channel.valueInfo()[0].type == "counter"


def test_preset_info_uses_channel_name(daemon_accumulator, poller_accumulator):
    assert daemon_accumulator.presetInfo() == {CHANNEL}
    assert poller_accumulator.presetInfo() == {CHANNEL}


def test_status_is_idle_before_start(
    device_harness, daemon_accumulator, poller_accumulator
):
    assert device_harness.run_daemon(daemon_accumulator.status, 0) == (
        status.OK,
        "",
    )
    assert device_harness.run_poller(poller_accumulator.status, 0) == (
        status.OK,
        "",
    )


def test_status_is_busy_while_started(
    device_harness, daemon_accumulator, poller_accumulator
):
    device_harness.run_daemon(daemon_accumulator.start)
    assert device_harness.run_daemon(daemon_accumulator.status, 0) == (
        status.BUSY,
        "counting",
    )
    assert device_harness.run_poller(poller_accumulator.status, 0) == (
        status.BUSY,
        "counting",
    )


def test_idle_status_uses_kafka_alarm_status(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    emit_alarm(
        device_harness,
        kafka_readback_stubs,
        time.time(),
        severity=Severity.MAJOR,
        message="fault",
    )
    assert device_harness.run_daemon(daemon_accumulator.status, 0) == (
        status.ERROR,
        "fault",
    )
    assert device_harness.run_daemon(daemon_accumulator.status) == (
        status.ERROR,
        "fault",
    )
    assert device_harness.run_poller(poller_accumulator.status) == (
        status.ERROR,
        "fault",
    )


def test_minor_alarm_status_stays_busy_while_started(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_alarm(
        device_harness,
        kafka_readback_stubs,
        time.time(),
        severity=Severity.MINOR,
        message="drift",
    )
    assert device_harness.run_daemon(daemon_accumulator.status, 0) == (
        status.BUSY,
        "counting, drift",
    )
    assert device_harness.run_daemon(daemon_accumulator.status) == (
        status.BUSY,
        "counting, drift",
    )
    assert device_harness.run_poller(poller_accumulator.status) == (
        status.BUSY,
        "counting, drift",
    )


def test_connection_error_status_overrides_busy(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_connection(
        device_harness,
        kafka_readback_stubs,
        time.time(),
        connection=ConnectionInfo.DISCONNECTED,
    )
    assert device_harness.run_daemon(daemon_accumulator.status, 0) == (
        status.ERROR,
        "counting, Kafka source disconnected (svc)",
    )
    assert device_harness.run_daemon(daemon_accumulator.status) == (
        status.ERROR,
        "counting, Kafka source disconnected (svc)",
    )
    assert device_harness.run_poller(poller_accumulator.status) == (
        status.ERROR,
        "counting, Kafka source disconnected (svc)",
    )


def test_unknown_connection_status_overrides_busy(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_connection(
        device_harness,
        kafka_readback_stubs,
        time.time(),
        connection=ConnectionInfo.UNKNOWN,
    )
    assert device_harness.run_daemon(daemon_accumulator.status, 0) == (
        status.UNKNOWN,
        "counting, Kafka source unknown (svc)",
    )
    assert device_harness.run_daemon(daemon_accumulator.status) == (
        status.UNKNOWN,
        "counting, Kafka source unknown (svc)",
    )
    assert device_harness.run_poller(poller_accumulator.status) == (
        status.UNKNOWN,
        "counting, Kafka source unknown (svc)",
    )


def test_cached_status_follows_daemon_start_and_finish(
    device_harness, daemon_accumulator, poller_accumulator
):
    assert device_harness.run_daemon(daemon_accumulator.status) == (status.OK, "")
    assert device_harness.run_poller(poller_accumulator.status) == (status.OK, "")

    device_harness.run_daemon(daemon_accumulator.start)
    assert device_harness.run_daemon(daemon_accumulator.status) == (
        status.BUSY,
        "counting",
    )
    assert device_harness.run_poller(poller_accumulator.status) == (
        status.BUSY,
        "counting",
    )

    device_harness.run_daemon(daemon_accumulator.finish)
    assert device_harness.run_daemon(daemon_accumulator.status) == (status.OK, "")
    assert device_harness.run_poller(poller_accumulator.status) == (status.OK, "")


def test_ignores_values_before_start(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    emit_value(device_harness, kafka_readback_stubs, 2.0, 1.0)
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        0.0
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        0.0
    )


def test_sums_f144_values_while_started(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_deltas(device_harness, kafka_readback_stubs, [0.5, 1.25, 2.0])
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        3.75
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        3.75
    )


def test_sums_repeated_f144_values_while_started(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_deltas(device_harness, kafka_readback_stubs, [2.0, 2.0])
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        4.0
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        4.0
    )


def test_sums_negative_f144_values_while_started(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_deltas(device_harness, kafka_readback_stubs, [-1.5, 2.0])
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        0.5
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        0.5
    )


def test_ignores_values_older_than_start(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_value(device_harness, kafka_readback_stubs, 5.0, 1.0)
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        0.0
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        0.0
    )


def test_alarm_update_does_not_replay_previous_value(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_value(device_harness, kafka_readback_stubs, 3.0, time.time())
    emit_alarm(device_harness, kafka_readback_stubs, time.time())
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        3.0
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        3.0
    )


def test_connection_update_does_not_replay_previous_value(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_value(device_harness, kafka_readback_stubs, 3.0, time.time())
    emit_connection(device_harness, kafka_readback_stubs, time.time())
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        3.0
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        3.0
    )


def test_prepare_resets_total(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_value(device_harness, kafka_readback_stubs, 4.0, time.time())
    device_harness.run_daemon(daemon_accumulator.prepare)
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        0.0
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        0.0
    )
    assert device_harness.run_daemon(daemon_accumulator.status, 0) == (
        status.OK,
        "",
    )
    assert device_harness.run_poller(poller_accumulator.status, 0) == (
        status.OK,
        "",
    )


def test_start_resets_total(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_value(device_harness, kafka_readback_stubs, 4.0, time.time())
    device_harness.run_daemon(daemon_accumulator.start)
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        0.0
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        0.0
    )


def test_finish_keeps_final_total(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    emit_value(device_harness, kafka_readback_stubs, 4.0, time.time())
    device_harness.run_daemon(daemon_accumulator.finish)
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        4.0
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        4.0
    )
    assert device_harness.run_daemon(daemon_accumulator.status, 0) == (
        status.OK,
        "",
    )
    assert device_harness.run_poller(poller_accumulator.status, 0) == (
        status.OK,
        "",
    )


def test_finish_stops_accumulation(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    device_harness.run_daemon(daemon_accumulator.finish)
    emit_value(device_harness, kafka_readback_stubs, 4.0, time.time())
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        0.0
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        0.0
    )


def test_stop_stops_accumulation(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_accumulator.start)
    device_harness.run_daemon(daemon_accumulator.stop)
    emit_value(device_harness, kafka_readback_stubs, 4.0, time.time())
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        0.0
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        0.0
    )


def test_detector_soft_preset_waits_below_target(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    daemon_detector,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_detector.setPreset, proton_acc=10)
    device_harness.run_daemon(daemon_detector.prepare)
    device_harness.run_daemon(daemon_detector.start)
    emit_value(device_harness, kafka_readback_stubs, 9.5, time.time())
    assert not device_harness.run_daemon(daemon_detector.isCompleted)
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        9.5
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        9.5
    )


def test_detector_soft_preset_completes_at_target(
    device_harness,
    daemon_accumulator,
    poller_accumulator,
    daemon_detector,
    kafka_readback_stubs,
):
    device_harness.run_daemon(daemon_detector.setPreset, proton_acc=10)
    device_harness.run_daemon(daemon_detector.prepare)
    device_harness.run_daemon(daemon_detector.start)
    emit_value(device_harness, kafka_readback_stubs, 10.0, time.time())
    assert device_harness.run_daemon(daemon_detector.isCompleted)
    assert device_harness.run_daemon(daemon_accumulator.read)[0] == pytest.approx(
        10.0
    )
    assert device_harness.run_poller(poller_accumulator.read)[0] == pytest.approx(
        10.0
    )


def publish_count_values(subscribers, channel, values):
    assert wait_until(lambda: channel.started)
    publish_deltas(subscribers, values)


def test_count_accepts_accumulator_preset(session, kafka_readback_stubs):
    with loaded_setup(session, "ess_accumulator_count_scan"):
        set_detectors(session, "detector")
        channel = session.getDevice(CHANNEL)
        publisher = threading.Thread(
            target=publish_count_values,
            args=(kafka_readback_stubs, channel, [4.0, 7.0]),
            daemon=True,
        )
        publisher.start()
        count(proton_acc=10)
        publisher.join(timeout=1)
        assert not publisher.is_alive()
        assert channel.read()[0] == pytest.approx(11.0)
