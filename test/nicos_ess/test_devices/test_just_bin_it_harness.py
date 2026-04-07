# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************
import json
import time

import pytest

from nicos.core import status

from nicos_ess.devices.datasources import just_bin_it
from nicos_ess.devices.kafka import status_handler
from nicos_ess.devices.timer import TimerChannel

from test.nicos_ess.test_devices.doubles import StubKafkaConsumer, \
    StubKafkaProducer, StubKafkaSubscriber


@pytest.fixture
def kafka_stubs(monkeypatch):
    monkeypatch.setattr(just_bin_it, "KafkaSubscriber", StubKafkaSubscriber)
    monkeypatch.setattr(
        just_bin_it.KafkaConsumer, "create", lambda *args, **kwargs: StubKafkaConsumer()
    )
    monkeypatch.setattr(
        just_bin_it.KafkaProducer, "create", lambda *args, **kwargs: StubKafkaProducer()
    )
    monkeypatch.setattr(status_handler, "KafkaSubscriber", StubKafkaSubscriber)


class RecordingKafkaProducer:
    def __init__(self):
        self.messages = []

    def produce(self, topic, message, **kwargs):
        self.messages.append((topic, message))
        callback = kwargs.get("on_delivery_callback")
        if callback:
            callback(None, object())


class _AckMessage:
    def __init__(self, payload):
        self._payload = payload

    def value(self):
        return self._payload


class AckingKafkaConsumer:
    def __init__(self, producer):
        self._producer = producer
        self._acked_ids = set()

    def subscribe(self, *_args, **_kwargs):
        pass

    def poll(self, timeout_ms=0):
        for _, message in self._producer.messages:
            try:
                payload = json.loads(message.decode("utf-8"))
            except Exception:
                continue
            if payload.get("cmd") != "config":
                continue
            msg_id = payload["msg_id"]
            if msg_id in self._acked_ids:
                continue
            self._acked_ids.add(msg_id)
            return _AckMessage(
                json.dumps({"msg_id": msg_id, "response": "ACK"}).encode("utf-8")
            )
        return None

    def close(self):
        pass


@pytest.fixture
def recording_kafka(monkeypatch):
    producer = RecordingKafkaProducer()
    consumer = AckingKafkaConsumer(producer)
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


class TestJustBinItImageHarness:
    def test_initializes(self, device_harness, kafka_stubs):
        daemon_device, poller_device = device_harness.create_pair(
            just_bin_it.JustBinItImage,
            name="just_bin_it_image",
            shared={
                "brokers": ["localhost:9092"],
                "hist_topic": "jbi_hist",
                "data_topic": "jbi_data",
            },
        )

        assert daemon_device is not None
        assert poller_device is not None


class TestJustBinItDetectorHarness:
    def test_initializes(self, device_harness, kafka_stubs):
        del kafka_stubs
        daemon_device, poller_device = device_harness.create_pair(
            just_bin_it.JustBinItDetector,
            name="just_bin_it_detector",
            shared={
                "brokers": ["localhost:9092"],
                "command_topic": "jbi_command",
                "response_topic": "jbi_response",
                "statustopic": [],
            },
        )

        assert daemon_device is not None
        assert poller_device is not None

    def test_start_publishes_config_and_finish_sends_one_stop(
        self, daemon_device_harness, recording_kafka
    ):
        detector = _create_detector(daemon_device_harness)

        detector.prepare()
        detector.start()
        time.sleep(0.05)
        detector.finish()

        commands = [
            json.loads(message.decode("utf-8"))["cmd"]
            for _, message in recording_kafka.messages
        ]
        assert commands.count("config") == 1
        assert commands.count("stop") == 1
        assert detector.status(0)[0] != status.ERROR

    def test_disconnect_and_recovery_follow_kafka_status_contract(
        self, daemon_device_harness, recording_kafka
    ):
        detector = _create_detector(
            daemon_device_harness, statustopic=["jbi_heartbeat"]
        )

        detector._next_update = time.time() - 10
        detector.no_messages_callback()
        assert detector.status(0) == (status.ERROR, "Disconnected")

        detector._cache.put(detector, "status", (status.ERROR, "Disconnected"), time.time())
        detector._status_update_callback({})
        assert detector.status(0)[0] != status.ERROR
