"""Command-level tests for just-bin-it count/scan integration.

These tests deliberately avoid a full Kafka stack. Instead they record the
commands produced by the detector and inject the minimal acknowledgement or
histogram messages needed to drive the NICOS count loop forward.
"""

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

# The command tests load a dedicated custom setup instead of inheriting any
# instrument defaults from the session fixture.
session_setup = None
COUNT_TIMER_PRESET_SECONDS = 0.02
EXPLICIT_IMAGE_PRESET = 2


def _command_names(producer):
    """Return the ordered list of command names recorded by the stub producer."""
    commands = []
    for record in producer.messages:
        try:
            commands.append(json.loads(record["message"].decode("utf-8"))["cmd"])
        except Exception:
            continue
    return commands


def _publish_histogram_when_started(image, total):
    """Publish one histogram update accepted by the started image channel.

    The image only accepts histogram messages tagged with the unique id it put
    into the just-bin-it config request, so the helper waits until that id has
    been generated before publishing the fake histogram.
    """
    assert wait_until(lambda: image._unique_id is not None)
    data = np.zeros(image.num_bins, dtype=np.float64)
    # Put all counts into the first bin so `image.read()[0]` equals `total`.
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
    """Patch just-bin-it Kafka classes with controllable in-memory doubles.

    The consumer looks at what the detector has produced and returns exactly
    one ACK for each config command. That mirrors the protocol the detector is
    written against without hiding the command traffic from the test.
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
    monkeypatch.setattr(just_bin_it.KafkaProducer, "create", lambda *a, **k: producer)
    monkeypatch.setattr(just_bin_it.KafkaConsumer, "create", lambda *a, **k: consumer)
    monkeypatch.setattr(status_handler, "KafkaSubscriber", StubKafkaSubscriber)
    return producer


def test_just_bin_it_count_with_timer_preset(session, jbi_backend):
    """Timer-controlled counts should send one config and one stop command.

    The simplified detector now starts just-bin-it in open-ended mode and lets
    the generic NICOS timer controller stop it afterwards.
    """
    with loaded_setup(session, "ess_just_bin_it_count_scan"):
        set_detectors(session, "jbi_detector")
        count(t=COUNT_TIMER_PRESET_SECONDS)
        assert _command_names(jbi_backend) == ["config", "stop"]


def test_just_bin_it_count_with_explicit_channel_preset(session, jbi_backend):
    """A channel preset should make that image the soft controller.

    Only `image_1` receives a histogram update here because `count(image_1=2)`
    is specifically testing the branch-local behaviour where the generic
    detector maps the preset to the matching image channel.
    """
    with loaded_setup(session, "ess_just_bin_it_count_scan"):
        set_detectors(session, "jbi_detector")
        image = session.getDevice("image_1")
        publisher = threading.Thread(
            target=_publish_histogram_when_started,
            args=(image, EXPLICIT_IMAGE_PRESET),
            daemon=True,
        )
        publisher.start()
        count(image_1=EXPLICIT_IMAGE_PRESET)
        publisher.join(timeout=1)
        assert not publisher.is_alive()
        assert image.read()[0] == EXPLICIT_IMAGE_PRESET
        assert _command_names(jbi_backend) == ["config", "stop"]


def test_just_bin_it_scan_across_two_points(session, jbi_backend):
    """A two-point scan should repeat the full config/start/stop cycle twice."""
    with loaded_setup(session, "ess_just_bin_it_count_scan"):
        set_detectors(session, "jbi_detector")
        axis = session.getDevice("axis")
        scan(axis, 0, 1, 2, t=COUNT_TIMER_PRESET_SECONDS)
        assert _command_names(jbi_backend).count("config") == 2
        assert _command_names(jbi_backend).count("stop") == 2
