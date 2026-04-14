# ruff: noqa: E402
import pytest

pytest.importorskip("streaming_data_types")

from streaming_data_types.alarm_al00 import Severity, serialise_al00
from streaming_data_types.epics_connection_ep01 import ConnectionInfo, serialise_ep01
from streaming_data_types.logdata_f144 import serialise_f144

from nicos.core import status
from nicos.core.errors import ConfigurationError
from nicos_ess.devices.kafka import readback

from test.nicos_ess.test_devices.doubles import StubKafkaSubscriber

READBACK_TOPIC = "readbacks"
READBACK_SOURCE = "src:first"
READBACK_SERVICE = "svc"


@pytest.fixture
def kafka_readback_stubs(monkeypatch):
    subscribers = []

    def create_subscriber(*args, **kwargs):
        subscriber = StubKafkaSubscriber(*args, **kwargs)
        subscribers.append(subscriber)
        return subscriber

    monkeypatch.setattr(readback, "KafkaSubscriber", create_subscriber)
    return subscribers


def alarm_message(timestamp_ns, severity, message):
    return serialise_al00(READBACK_SOURCE, timestamp_ns, severity, message)


def connection_message(timestamp_ns, connection, service=READBACK_SERVICE):
    return serialise_ep01(timestamp_ns, connection, READBACK_SOURCE, service)


def create_consumer_pair(harness, name="KafkaReadbacks", topics=None):
    return harness.create_pair(
        readback.KafkaReadbackConsumer,
        name=name,
        shared={
            "brokers": ["localhost:9092"],
            "topics": topics or [READBACK_TOPIC],
        },
    )


def create_readable_pair(harness, name, source_name, topic=READBACK_TOPIC):
    return harness.create_pair(
        readback.KafkaReadable,
        name=name,
        shared={
            "kafka": "KafkaReadbacks",
            "topic": topic,
            "source_name": source_name,
            "unit": "mm",
        },
    )


def emit_readback_messages(
    device_harness, subscribers, *payloads, topic=READBACK_TOPIC
):
    subscriber = next(
        subscriber
        for subscriber in subscribers
        if subscriber.subscribed and subscriber.subscribed[-1] == [topic]
    )
    batch = [((0, 0), payload) for payload in payloads]
    device_harness.run_daemon(subscriber.emit_messages, batch)


class TestKafkaReadbackHarness:
    def test_shared_consumer_fans_out_by_topic_and_source(
        self, device_harness, kafka_readback_stubs
    ):
        create_consumer_pair(device_harness)
        first, _poller_first = create_readable_pair(
            device_harness, "first", "src:first"
        )
        second, _poller_second = create_readable_pair(
            device_harness, "second", "src:second"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            serialise_f144("src:first", 1.5, 1_000_000_000),
            serialise_f144("src:second", 2.5, 2_000_000_000),
        )

        assert len(kafka_readback_stubs) == 1
        assert kafka_readback_stubs[0].brokers == ["localhost:9092"]
        assert kafka_readback_stubs[0].subscribed == [["readbacks"]]
        assert first.read() == pytest.approx(1.5)
        assert second.read() == pytest.approx(2.5)

    def test_register_gets_latest_snapshot(self, device_harness, kafka_readback_stubs):
        create_consumer_pair(device_harness)
        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            serialise_f144("src:first", 3.5, 3_000_000_000),
        )
        readable, poller_readable = create_readable_pair(
            device_harness, "first", "src:first"
        )

        assert readable.read() == pytest.approx(3.5)
        assert poller_readable.read() == pytest.approx(3.5)

    @pytest.mark.parametrize(
        ("messages", "expected"),
        [
            pytest.param(
                [alarm_message(1_000_000_000, Severity.MINOR, "HIGH")],
                (status.WARN, "HIGH"),
                id="minor-alarm",
            ),
            pytest.param(
                [
                    alarm_message(1_000_000_000, Severity.MINOR, "HIGH"),
                    connection_message(2_000_000_000, ConnectionInfo.CONNECTED),
                ],
                (status.WARN, "HIGH"),
                id="minor-alarm-overrides-connected",
            ),
            pytest.param(
                [
                    connection_message(2_000_000_000, ConnectionInfo.CONNECTED),
                    alarm_message(3_000_000_000, Severity.OK, ""),
                ],
                (status.OK, ""),
                id="ok-alarm-with-connected",
            ),
            pytest.param(
                [
                    alarm_message(3_000_000_000, Severity.OK, ""),
                    connection_message(
                        4_000_000_000, ConnectionInfo.DISCONNECTED
                    ),
                ],
                (status.ERROR, "Kafka source disconnected (svc)"),
                id="disconnected-connection",
            ),
        ],
    )
    def test_al00_and_ep01_drive_readable_status_matrix(
        self, device_harness, kafka_readback_stubs, messages, expected
    ):
        create_consumer_pair(device_harness)
        readable, poller_readable = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(device_harness, kafka_readback_stubs, *messages)

        assert readable.status(0) == expected
        assert readable.status() == expected
        assert poller_readable.status() == expected

    def test_shared_consumer_starts_one_subscriber_per_topic(
        self, device_harness, kafka_readback_stubs
    ):
        create_consumer_pair(
            device_harness,
            topics=["readbacks", "other_readbacks"],
        )

        assert len(kafka_readback_stubs) == 2
        assert [subscriber.subscribed for subscriber in kafka_readback_stubs] == [
            [["readbacks"]],
            [["other_readbacks"]],
        ]

    def test_readable_rejects_topic_not_owned_by_shared_consumer(
        self, device_harness, kafka_readback_stubs
    ):
        create_consumer_pair(device_harness)

        with pytest.raises(ConfigurationError):
            create_readable_pair(
                device_harness,
                "first",
                "src:first",
                topic="other_topic",
            )

    def test_poller_readable_uses_cache_and_does_not_create_kafka_consumer(
        self, device_harness, kafka_readback_stubs
    ):
        _daemon_consumer, _poller_consumer = create_consumer_pair(device_harness)
        daemon_readable, poller_readable = create_readable_pair(
            device_harness, "first", "src:first"
        )

        assert daemon_readable.maxage is None
        assert poller_readable.maxage is None
        assert len(kafka_readback_stubs) == 1
        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            serialise_f144("src:first", 4.5, 4_000_000_000),
        )

        assert device_harness.run_daemon(daemon_readable.read) == pytest.approx(4.5)
        assert device_harness.run_poller(poller_readable.read) == pytest.approx(4.5)
