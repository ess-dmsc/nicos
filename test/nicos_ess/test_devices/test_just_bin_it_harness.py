"""Harness tests for the simplified just-bin-it device graph.

The tests use small Kafka doubles so the non-obvious protocol steps stay
visible in the fixture code:

- config commands are produced by the detector
- the test fixture decides when an ACK appears
- histogram messages are injected explicitly when a test needs data
"""

import json
import time

import numpy as np
import pytest
from streaming_data_types import serialise_hs01

from nicos.core import status
from nicos_ess.devices.datasources import just_bin_it
from nicos_ess.devices.kafka import status_handler
from nicos_ess.devices.timer import TimerChannel
from test.nicos_ess.command_helpers import wait_until
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
    request/acknowledgement flow. Set `ack = False` on it to never answer.
    """
    producer = StubKafkaProducer()
    producer.ack = True
    acked_ids = set()

    def poll_hook(_consumer, timeout_ms=0):
        del timeout_ms
        if not producer.ack:
            return None
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
            return json.dumps({"msg_id": msg_id, "response": "ACK"}).encode("utf-8")
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


def _commands(producer):
    return [json.loads(r["message"].decode("utf-8")) for r in producer.messages]


def _send_histogram(detector, unique_id, state, total, num_bins=4):
    """Deliver one hs01 histogram with `total` in the first bin to the detector."""
    data = np.zeros(num_bins, dtype=np.float64)
    data[0] = total
    message = serialise_hs01(
        {
            "source": "jbi",
            "timestamp": 0,
            "current_shape": [num_bins],
            "dim_metadata": [
                {
                    "length": num_bins,
                    "bin_boundaries": np.arange(num_bins + 1, dtype=np.float64),
                }
            ],
            "data": data,
            "info": json.dumps({"id": unique_id, "state": state}),
        }
    )
    detector._hist_subscriber.emit_messages([(0, message)])


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
        finish_timeout=0.5,
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

    def test_image_input_schema_overrides_detector_default(
        self, daemon_device_harness, recording_kafka
    ):
        """A single image channel can override the detector input schema."""
        daemon_device_harness.create_master(
            TimerChannel,
            name="timer",
            update_interval=0.01,
        )

        for name, overrides in [
            ("ev44_image_1", {}),
            ("ev44_image_2", {}),
            ("da00_image", {"input_schema": "da00"}),
        ]:
            image_config = {
                "brokers": ["localhost:9092"],
                "hist_topic": "jbi_hist",
                "data_topic": "jbi_data",
                "hist_type": "1-D TOF",
                "num_bins": 4,
                "rotation": 0,
            }
            image_config.update(overrides)
            daemon_device_harness.create_master(
                just_bin_it.JustBinItImage,
                name=name,
                **image_config,
            )

        detector = daemon_device_harness.create_master(
            just_bin_it.JustBinItDetector,
            name="just_bin_it_detector",
            brokers=["localhost:9092"],
            command_topic="jbi_command",
            response_topic="jbi_response",
            event_schema="ev44",
            statustopic=[],
            images=["ev44_image_1", "ev44_image_2", "da00_image"],
            timers=["timer"],
        )

        detector.prepare()
        detector.start()
        time.sleep(ACK_WAIT_SECONDS)
        detector.finish()

        config = next(
            command
            for record in recording_kafka.messages
            for command in [json.loads(record["message"].decode("utf-8"))]
            if command["cmd"] == "config"
        )

        assert config["input_schema"] == "ev44"
        assert "input_schema" not in config["histograms"][0]
        assert "input_schema" not in config["histograms"][1]
        assert config["histograms"][2]["input_schema"] == "da00"

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


class TestJustBinItFinalHistograms:
    def test_finished_histogram_is_the_value_read(
        self, daemon_device_harness, recording_kafka
    ):
        detector = _create_detector(daemon_device_harness)
        image = detector._attached_images[0]
        detector.prepare()
        detector.start()
        channel_id = image._unique_id
        _send_histogram(detector, channel_id, "COUNTING", 5)
        assert image.read()[0] == 5
        _send_histogram(detector, channel_id, "FINISHED", 12)
        detector.finish()
        assert image.read()[0] == 12
        assert image.finished

    def test_messages_of_other_jobs_are_ignored(
        self, daemon_device_harness, recording_kafka
    ):
        detector = _create_detector(daemon_device_harness)
        image = detector._attached_images[0]
        detector.prepare()
        detector.start()
        old_id = image._unique_id
        _send_histogram(detector, old_id, "FINISHED", 9)
        detector.finish()

        detector.prepare()
        _send_histogram(detector, old_id, "FINISHED", 99)
        detector.start()
        _send_histogram(detector, old_id, "FINISHED", 99)
        assert image.read()[0] == 0
        assert not image.finished
        assert image._unique_id != old_id

    def test_timer_preset_sends_window_and_no_stop(
        self, daemon_device_harness, recording_kafka
    ):
        detector = _create_detector(daemon_device_harness)
        image = detector._attached_images[0]
        detector.setPreset(t=0.05)
        detector.prepare()
        before = int(time.time() * 1000)
        detector.start()
        assert wait_until(detector.isCompleted)
        _send_histogram(detector, image._unique_id, "FINISHED", 3)
        detector.finish()
        commands = _commands(recording_kafka)
        assert [c["cmd"] for c in commands] == ["config"]
        assert commands[0]["start"] >= before
        assert commands[0]["stop"] - commands[0]["start"] == 50

    def test_mixed_preset_ended_by_the_timer_uses_the_window(
        self, daemon_device_harness, recording_kafka
    ):
        detector = _create_detector(daemon_device_harness)
        image = detector._attached_images[0]
        detector.setPreset(t=0.05, image_1=10**9)
        detector.prepare()
        detector.start()
        assert wait_until(detector.isCompleted)
        _send_histogram(detector, image._unique_id, "FINISHED", 3)
        detector.finish()
        (config,) = _commands(recording_kafka)
        assert config["stop"] - config["start"] == 50
        assert [c["cmd"] for c in _commands(recording_kafka)] == ["config"]
        assert image.read()[0] == 3

    def test_missing_final_histogram_warns_and_keeps_last_values(
        self, daemon_device_harness, recording_kafka, caplog
    ):
        detector = _create_detector(daemon_device_harness)
        image = detector._attached_images[0]
        detector.log.addHandler(caplog.handler)
        detector.setPreset(t=0.05)
        detector.prepare()
        detector.start()
        _send_histogram(detector, image._unique_id, "COUNTING", 4)
        assert wait_until(detector.isCompleted)
        start = time.monotonic()
        detector.finish()
        assert 0.4 < time.monotonic() - start < 2
        assert image.read()[0] == 4
        assert not image.finished
        assert image.status(0)[0] == status.OK
        assert "no final histogram" in caplog.text

    def test_error_histogram_ends_the_wait(
        self, daemon_device_harness, recording_kafka
    ):
        detector = _create_detector(daemon_device_harness)
        image = detector._attached_images[0]
        detector.setPreset(t=0.01)
        detector.prepare()
        detector.start()
        assert wait_until(detector.isCompleted)
        _send_histogram(detector, image._unique_id, "ERROR", 0)
        start = time.monotonic()
        detector.finish()
        assert time.monotonic() - start < 0.3
        assert image.status(0)[0] == status.WARN

    def test_stopped_count_keeps_last_update(
        self, daemon_device_harness, recording_kafka
    ):
        detector = _create_detector(daemon_device_harness)
        image = detector._attached_images[0]
        detector.prepare()
        detector.start()
        channel_id = image._unique_id
        _send_histogram(detector, channel_id, "COUNTING", 4)
        start = time.monotonic()
        detector.finish()
        assert time.monotonic() - start < 0.4
        _send_histogram(detector, channel_id, "FINISHED", 40)
        assert image.read()[0] == 4
        assert image.status(0)[0] == status.OK
        assert [c["cmd"] for c in _commands(recording_kafka)] == ["config", "stop"]

    def test_count_finished_before_ack_sends_no_stop(
        self, daemon_device_harness, recording_kafka
    ):
        recording_kafka.ack = False
        detector = _create_detector(daemon_device_harness)
        image = detector._attached_images[0]
        detector.setPreset(t=0.01)
        detector.prepare()
        detector.start()
        assert wait_until(detector.isCompleted)
        _send_histogram(detector, image._unique_id, "FINISHED", 2)
        detector.finish()
        assert image.read()[0] == 2
        assert [c["cmd"] for c in _commands(recording_kafka)] == ["config"]

    def test_stopped_count_without_ack_warns(
        self, daemon_device_harness, recording_kafka, caplog
    ):
        recording_kafka.ack = False
        detector = _create_detector(daemon_device_harness)
        detector.log.addHandler(caplog.handler)
        detector.prepare()
        detector.start()
        detector.finish()
        assert "did not acknowledge" in caplog.text

    def test_shutdown_closes_heartbeat_subscriber(
        self, daemon_device_harness, recording_kafka
    ):
        detector = _create_detector(daemon_device_harness, statustopic=["jbi_hb"])
        heartbeat = detector._kafka_subscriber
        detector.shutdown()
        assert heartbeat.closed
