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


def create_router_pair(harness, name="KafkaReadbacks", topics=None):
    return harness.create_pair(
        readback.KafkaReadbackRouter,
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
    def test_shared_router_fans_out_by_topic_and_source(
        self, device_harness, kafka_readback_stubs
    ):
        create_router_pair(device_harness)
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
        create_router_pair(device_harness)
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
        create_router_pair(device_harness)
        readable, poller_readable = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(device_harness, kafka_readback_stubs, *messages)

        assert readable.status(0) == expected
        assert readable.status() == expected
        assert poller_readable.status() == expected

    def test_shared_router_starts_one_subscriber_per_topic(
        self, device_harness, kafka_readback_stubs
    ):
        create_router_pair(
            device_harness,
            topics=["readbacks", "other_readbacks"],
        )

        assert len(kafka_readback_stubs) == 2
        assert [subscriber.subscribed for subscriber in kafka_readback_stubs] == [
            [["readbacks"]],
            [["other_readbacks"]],
        ]

    def test_readable_rejects_topic_not_owned_by_shared_router(
        self, device_harness, kafka_readback_stubs
    ):
        create_router_pair(device_harness)

        with pytest.raises(ConfigurationError):
            create_readable_pair(
                device_harness,
                "first",
                "src:first",
                topic="other_topic",
            )

    def test_poller_readable_uses_cache_and_poller_router_does_not_subscribe(
        self, device_harness, kafka_readback_stubs
    ):
        _daemon_router, _poller_router = create_router_pair(device_harness)
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

    def test_doread_raises_before_any_messages(
        self, device_harness, kafka_readback_stubs
    ):
        """doRead raises CommunicationError when no Kafka messages have arrived yet."""
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        with pytest.raises(readback.CommunicationError):
            readable.read()

    def test_dostatus_returns_unknown_before_any_messages(
        self, device_harness, kafka_readback_stubs
    ):
        """doStatus returns UNKNOWN when no Kafka messages have arrived yet."""
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        assert readable.status() == (status.UNKNOWN, "No status information")

    def test_doread_raises_communication_error_when_only_alarm_received(
        self, device_harness, kafka_readback_stubs
    ):
        """An alarm-only message does not produce a readable value."""
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            alarm_message(1_000_000_000, Severity.MINOR, "HIGH"),
        )

        with pytest.raises(readback.CommunicationError):
            readable.read()

    def test_doread_raises_communication_error_when_only_connection_received(
        self, device_harness, kafka_readback_stubs
    ):
        """A connection-only message does not produce a readable value."""
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            connection_message(1_000_000_000, ConnectionInfo.CONNECTED),
        )

        with pytest.raises(readback.CommunicationError):
            readable.read()

    def test_dostatus_returns_unknown_when_only_value_received(
        self, device_harness, kafka_readback_stubs
    ):
        """f144 alone carries no alarm/connection info → status stays UNKNOWN."""
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            serialise_f144("src:first", 1.0, 1_000_000_000),
        )

        assert readable.status() == (status.UNKNOWN, "No status information")

    def test_doread_preserves_value_after_alarm_update(
        self, device_harness, kafka_readback_stubs
    ):
        """Value remains readable after a subsequent alarm-only message."""
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            serialise_f144("src:first", 7.7, 1_000_000_000),
        )
        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            alarm_message(2_000_000_000, Severity.MINOR, "drift"),
        )

        assert readable.read() == pytest.approx(7.7)
        assert readable.status() == (status.WARN, "drift")

    @pytest.mark.parametrize(
        ("severity", "expected_status", "message"),
        [
            pytest.param(Severity.OK, status.OK, "", id="ok"),
            pytest.param(Severity.MINOR, status.WARN, "drifting", id="minor"),
            pytest.param(Severity.MAJOR, status.ERROR, "out of range", id="major"),
            pytest.param(Severity.INVALID, status.ERROR, "sensor fault", id="invalid"),
        ],
    )
    def test_alarm_severity_maps_to_nicos_status(
        self, device_harness, kafka_readback_stubs,
        severity, expected_status, message,
    ):
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            alarm_message(1_000_000_000, severity, message),
        )

        assert readable.status() == (expected_status, message)

    @pytest.mark.parametrize(
        ("connection", "expected_status", "expected_message"),
        [
            pytest.param(
                ConnectionInfo.CONNECTED, status.OK, "",
                id="connected",
            ),
            pytest.param(
                ConnectionInfo.DISCONNECTED, status.ERROR,
                "Kafka source disconnected (svc)",
                id="disconnected",
            ),
            pytest.param(
                ConnectionInfo.DESTROYED, status.ERROR,
                "Kafka source destroyed (svc)",
                id="destroyed",
            ),
            pytest.param(
                ConnectionInfo.CANCELLED, status.ERROR,
                "Kafka source cancelled (svc)",
                id="cancelled",
            ),
            pytest.param(
                ConnectionInfo.FINISHED, status.ERROR,
                "Kafka source finished (svc)",
                id="finished",
            ),
            pytest.param(
                ConnectionInfo.REMOTE_ERROR, status.ERROR,
                "Kafka source remote_error (svc)",
                id="remote-error",
            ),
            pytest.param(
                ConnectionInfo.UNKNOWN, status.UNKNOWN,
                "Kafka source unknown (svc)",
                id="unknown",
            ),
            pytest.param(
                ConnectionInfo.NEVER_CONNECTED, status.UNKNOWN,
                "Kafka source never_connected (svc)",
                id="never-connected",
            ),
        ],
    )
    def test_connection_state_maps_to_nicos_status(
        self, device_harness, kafka_readback_stubs,
        connection, expected_status, expected_message,
    ):
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            connection_message(1_000_000_000, connection),
        )

        assert readable.status() == (expected_status, expected_message)

    @pytest.mark.parametrize(
        ("severity", "expected_status", "expected_default"),
        [
            pytest.param(
                Severity.MINOR, status.WARN,
                "Kafka alarm severity MINOR",
                id="minor",
            ),
            pytest.param(
                Severity.MAJOR, status.ERROR,
                "Kafka alarm severity MAJOR",
                id="major",
            ),
            pytest.param(
                Severity.INVALID, status.ERROR,
                "Kafka alarm severity INVALID",
                id="invalid",
            ),
        ],
    )
    def test_alarm_with_empty_message_uses_default_text(
        self, device_harness, kafka_readback_stubs,
        severity, expected_status, expected_default,
    ):
        """Non-OK alarms with no message text fall back to a severity label."""
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            alarm_message(1_000_000_000, severity, ""),
        )

        assert readable.status() == (expected_status, expected_default)

    def test_connection_status_omits_service_when_empty(
        self, device_harness, kafka_readback_stubs
    ):
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            connection_message(
                1_000_000_000, ConnectionInfo.DISCONNECTED, service=""
            ),
        )

        assert readable.status() == (
            status.ERROR,
            "Kafka source disconnected",
        )

    def test_latest_value_overwrites_previous(
        self, device_harness, kafka_readback_stubs
    ):
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            serialise_f144("src:first", 1.0, 1_000_000_000),
        )
        assert readable.read() == pytest.approx(1.0)

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            serialise_f144("src:first", 2.0, 2_000_000_000),
        )
        assert readable.read() == pytest.approx(2.0)

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(42, pytest.approx(42), id="integer"),
            pytest.param(3.14, pytest.approx(3.14), id="float"),
            pytest.param(-1.5, pytest.approx(-1.5), id="negative"),
            pytest.param(0, pytest.approx(0.0), id="zero"),
        ],
    )
    def test_doread_handles_various_value_types(
        self, device_harness, kafka_readback_stubs, value, expected
    ):
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            serialise_f144("src:first", value, 1_000_000_000),
        )

        assert readable.read() == expected

    def test_corrupt_kafka_payload_does_not_crash_router(
        self, device_harness, kafka_readback_stubs
    ):
        """Router silently skips garbage payloads it cannot decode."""
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            b"not_a_valid_flatbuffer",
        )

        with pytest.raises(readback.CommunicationError):
            readable.read()
        assert readable.status() == (status.UNKNOWN, "No status information")

    def test_value_survives_after_corrupt_payload(
        self, device_harness, kafka_readback_stubs
    ):
        """A corrupt payload does not discard previously received values."""
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            serialise_f144("src:first", 5.5, 1_000_000_000),
        )
        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            b"garbage",
        )

        assert readable.read() == pytest.approx(5.5)

    def test_messages_for_unknown_source_do_not_affect_registered_readable(
        self, device_harness, kafka_readback_stubs
    ):
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            serialise_f144("src:unknown", 99.0, 1_000_000_000),
        )

        with pytest.raises(readback.CommunicationError):
            readable.read()

    def test_multiple_readables_on_same_source_get_same_value(
        self, device_harness, kafka_readback_stubs
    ):
        create_router_pair(device_harness)
        first, _poller_first = create_readable_pair(
            device_harness, "first", "src:first"
        )
        second, _poller_second = create_readable_pair(
            device_harness, "second", "src:first",
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            serialise_f144("src:first", 3.0, 1_000_000_000),
        )

        assert first.read() == pytest.approx(3.0)
        assert second.read() == pytest.approx(3.0)

    def test_alarm_clears_from_error_back_to_ok(
        self, device_harness, kafka_readback_stubs
    ):
        """Verify that an alarm can transition from MAJOR → OK."""
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            alarm_message(1_000_000_000, Severity.MAJOR, "fault"),
        )
        assert readable.status() == (status.ERROR, "fault")

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            alarm_message(2_000_000_000, Severity.OK, ""),
        )
        assert readable.status() == (status.OK, "")

    def test_connection_recovers_from_disconnected_to_connected(
        self, device_harness, kafka_readback_stubs
    ):
        """Verify that a connection can transition from DISCONNECTED → CONNECTED."""
        create_router_pair(device_harness)
        readable, _poller = create_readable_pair(
            device_harness, "first", "src:first"
        )

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            connection_message(1_000_000_000, ConnectionInfo.DISCONNECTED),
        )
        assert readable.status()[0] == status.ERROR

        emit_readback_messages(
            device_harness,
            kafka_readback_stubs,
            connection_message(2_000_000_000, ConnectionInfo.CONNECTED),
        )
        assert readable.status() == (status.OK, "")

    def test_router_shutdown_closes_all_subscribers(
        self, device_harness, kafka_readback_stubs
    ):
        daemon_router, _poller_router = create_router_pair(
            device_harness,
            topics=["topic_a", "topic_b"],
        )

        device_harness.run_daemon(daemon_router.shutdown)

        assert all(sub.closed for sub in kafka_readback_stubs)
