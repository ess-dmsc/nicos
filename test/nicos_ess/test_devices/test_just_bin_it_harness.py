"""Harness tests for the simplified just-bin-it device graph.

The tests use small Kafka doubles so the non-obvious protocol steps stay
visible in the fixture code:

- config commands are produced by the detector
- the test fixture decides when an ACK appears
- histogram messages are injected explicitly when a test needs data
"""

import json
import time

import pytest

from nicos.core import status

from nicos_ess.devices.datasources import just_bin_it
from nicos_ess.devices.kafka import status_handler
from nicos_ess.devices.timer import TimerChannel

from test.nicos_ess.test_devices.doubles import (
    StubKafkaConsumer,
    StubKafkaProducer,
    StubKafkaSubscriber,
)

ACK_WAIT_SECONDS = 0.05


@pytest.fixture
def kafka_stubs(monkeypatch):
    """Patch all Kafka classes with inert doubles for pure init tests."""
    monkeypatch.setattr(just_bin_it, "KafkaSubscriber", StubKafkaSubscriber)
    monkeypatch.setattr(
        just_bin_it.KafkaConsumer, "create", lambda *args, **kwargs: StubKafkaConsumer()
    )
    monkeypatch.setattr(
        just_bin_it.KafkaProducer, "create", lambda *args, **kwargs: StubKafkaProducer()
    )
    monkeypatch.setattr(status_handler, "KafkaSubscriber", StubKafkaSubscriber)


@pytest.fixture
def recording_kafka(monkeypatch):
    """Provide a producer/consumer pair that records commands and auto-ACKs.

    The consumer inspects the producer's recorded messages and emits exactly
    one ACK for each `config` request, mirroring the detector's expected
    request/acknowledgement flow.
    """
    producer = StubKafkaProducer()
    acked_ids = set()

    def poll_hook(_consumer, timeout_ms=0):
        del timeout_ms
        for record in producer.messages:
            try:
                payload = json.loads(record["message"].decode("utf-8"))
            except Exception:
                continue
            if payload.get("cmd") != "config":
                continue
            msg_id = payload["msg_id"]
            if msg_id in acked_ids:
                continue
            acked_ids.add(msg_id)
            return json.dumps(
                {"msg_id": msg_id, "response": "ACK"}
            ).encode("utf-8")
        return None

    consumer = StubKafkaConsumer(poll_hook=poll_hook)
    monkeypatch.setattr(just_bin_it, "KafkaSubscriber", StubKafkaSubscriber)
    monkeypatch.setattr(
        just_bin_it.KafkaProducer, "create", lambda *args, **kwargs: producer
    )
    monkeypatch.setattr(
        just_bin_it.KafkaConsumer, "create", lambda *args, **kwargs: consumer
    )
    monkeypatch.setattr(status_handler, "KafkaSubscriber", StubKafkaSubscriber)
    return producer


def _create_detector(daemon_device_harness, *, statustopic=None):
    """Build the smallest complete just-bin-it detector graph used in tests."""
    daemon_device_harness.create_master(
        TimerChannel,
        name="timer",
        update_interval=0.01,
    )
    daemon_device_harness.create_master(
        just_bin_it.JustBinItImage,
        name="image_1",
        brokers=["localhost:9092"],
        hist_topic="jbi_hist",
        data_topic="jbi_data",
        hist_type="1-D TOF",
        num_bins=4,
        rotation=0,
    )
    return daemon_device_harness.create_master(
        just_bin_it.JustBinItDetector,
        name="just_bin_it_detector",
        brokers=["localhost:9092"],
        command_topic="jbi_command",
        response_topic="jbi_response",
        statustopic=statustopic or [],
        images=["image_1"],
        timers=["timer"],
    )


class TestJustBinItDetectorHarness:
    def test_full_detector_hierarchy_initializes_in_both_roles(
        self, device_harness, kafka_stubs
    ):
        """The aggregate detector and its image channel should init in both roles."""
        daemon_im, poller_im = device_harness.create_pair(
            just_bin_it.JustBinItImage,
            name="image_1",
            shared={
                "brokers": ["localhost:9092"],
                "hist_topic": "jbi_hist",
                "data_topic": "jbi_data",
            },
        )
        daemon_det, poller_det = device_harness.create_pair(
            just_bin_it.JustBinItDetector,
            name="just_bin_it_detector",
            shared={
                "brokers": ["localhost:9092"],
                "command_topic": "jbi_command",
                "response_topic": "jbi_response",
                "statustopic": [],
                "images": ["image_1"],
            },
        )

        assert daemon_im is not None
        assert poller_im is not None
        assert daemon_det is not None
        assert poller_det is not None

    def test_start_publishes_config_and_finish_sends_one_stop(
        self, daemon_device_harness, recording_kafka
    ):
        """Starting once should publish one config, and finishing should stop once."""
        detector = _create_detector(daemon_device_harness)

        detector.prepare()
        detector.start()
        # Give the ACK thread time to consume the synthetic acknowledgement.
        time.sleep(ACK_WAIT_SECONDS)
        detector.finish()

        commands = [
            json.loads(message.decode("utf-8"))["cmd"]
            for record in recording_kafka.messages
            for message in [record["message"]]
        ]
        assert commands.count("config") == 1
        assert commands.count("stop") == 1
        assert detector.status(0)[0] != status.ERROR

    def test_disconnect_and_recovery_follow_kafka_status_contract(
        self, daemon_device_harness, recording_kafka
    ):
        """Heartbeat loss should set the disconnect status and recovery should clear it."""
        detector = _create_detector(
            daemon_device_harness, statustopic=["jbi_heartbeat"]
        )

        detector._next_update = time.time() - 10
        detector.no_messages_callback()
        assert detector.status(0) == (status.ERROR, "Disconnected")

        detector._cache.put(
            detector, "status", (status.ERROR, "Disconnected"), time.time()
        )
        detector._status_update_callback({})
        assert detector.status(0)[0] != status.ERROR
