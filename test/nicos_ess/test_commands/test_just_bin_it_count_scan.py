import json
import threading
import time

import numpy as np
import pytest

pytest.importorskip("streaming_data_types")

from streaming_data_types import serialise_hs01

from nicos.commands.measure import count
from nicos.commands.scan import scan

from nicos_ess.devices.datasources import just_bin_it
from nicos_ess.devices.kafka import status_handler

from test.nicos_ess.command_helpers import loaded_setup, set_detectors, wait_until
from test.nicos_ess.test_devices.doubles import (
    StubKafkaConsumer,
    StubKafkaProducer,
    StubKafkaSubscriber,
)

session_setup = None


def _command_names(producer):
    commands = []
    for record in producer.messages:
        try:
            commands.append(json.loads(record["message"].decode("utf-8"))["cmd"])
        except Exception:
            continue
    return commands


def _publish_histogram_when_started(image, total):
    assert wait_until(lambda: image._unique_id is not None)
    data = np.zeros(image.num_bins, dtype=np.float64)
    data[0] = total
    message = serialise_hs01(
        {
            "source": image.hist_topic,
            "timestamp": int(time.time() * 1e9),
            "current_shape": [image.num_bins],
            "dim_metadata": [
                {
                    "length": image.num_bins,
                    "bin_boundaries": np.arange(image.num_bins + 1, dtype=np.float64),
                }
            ],
            "data": data,
            "info": json.dumps(
                {"id": image._unique_id, "state": "COUNTING", "rate": 0.0}
            ),
        }
    )
    image.new_messages_callback([(int(time.time() * 1e9), message)])


@pytest.fixture
def jbi_backend(monkeypatch):
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
    monkeypatch.setattr(just_bin_it.KafkaProducer, "create", lambda *a, **k: producer)
    monkeypatch.setattr(just_bin_it.KafkaConsumer, "create", lambda *a, **k: consumer)
    monkeypatch.setattr(status_handler, "KafkaSubscriber", StubKafkaSubscriber)
    return producer


def test_just_bin_it_count_with_timer_preset(session, jbi_backend):
    with loaded_setup(session, "ess_just_bin_it_count_scan"):
        set_detectors(session, "jbi_detector")
        count(t=0.02)
        assert _command_names(jbi_backend) == ["config", "stop"]


def test_just_bin_it_count_with_explicit_channel_preset(session, jbi_backend):
    with loaded_setup(session, "ess_just_bin_it_count_scan"):
        set_detectors(session, "jbi_detector")
        image = session.getDevice("image_1")
        publisher = threading.Thread(
            target=_publish_histogram_when_started, args=(image, 2), daemon=True
        )
        publisher.start()
        count(image_1=2)
        publisher.join(timeout=1)
        assert not publisher.is_alive()
        assert image.read()[0] == 2
        assert _command_names(jbi_backend) == ["config", "stop"]


def test_just_bin_it_scan_across_two_points(session, jbi_backend):
    with loaded_setup(session, "ess_just_bin_it_count_scan"):
        set_detectors(session, "jbi_detector")
        axis = session.getDevice("axis")
        scan(axis, 0, 1, 2, t=0.02)
        assert _command_names(jbi_backend).count("config") == 2
        assert _command_names(jbi_backend).count("stop") == 2
