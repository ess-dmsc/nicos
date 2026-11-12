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
from test.nicos_ess.command_helpers import loaded_setup, set_detectors
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


def _commands(producer):
    return [json.loads(r["message"].decode("utf-8")) for r in list(producer.messages)]


def _histogram(unique_id, state, total, num_bins):
    data = np.zeros(num_bins, dtype=np.float64)
    data[0] = total
    return serialise_hs01(
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


class JustBinItBackend(StubKafkaProducer):
    """Answer the latest config like just-bin-it: COUNTING, then FINISHED once.

    A job finishes when its stop time has passed or a stop command arrives.
    `totals` maps image names to the counts their histograms report.
    """

    def __init__(self):
        super().__init__()
        self.subscribers = []
        self.totals = {}
        self.stop = threading.Event()

    def subscribe(self, brokers):
        subscriber = StubKafkaSubscriber(brokers)
        self.subscribers.append(subscriber)
        return subscriber

    def run(self):
        finished = set()
        while not self.stop.wait(0.005):
            commands = _commands(self)
            configs = [c for c in commands if c["cmd"] == "config"]
            if not configs or configs[-1]["msg_id"] in finished:
                continue
            config = configs[-1]
            stopped = commands[commands.index(config) + 1 :] != []
            done = stopped or time.time() * 1000 >= config.get("stop", float("inf"))
            state = "FINISHED" if done else "COUNTING"
            messages = [
                (
                    0,
                    _histogram(
                        hist["id"],
                        state,
                        self.totals.get(hist["id"].rsplit("-", 1)[-1], 1),
                        hist["num_bins"],
                    ),
                )
                for hist in config["histograms"]
            ]
            for subscriber in self.subscribers:
                subscriber.emit_messages(messages)
            if done:
                finished.add(config["msg_id"])


@pytest.fixture
def jbi_backend(monkeypatch):
    """Patch just-bin-it Kafka classes with controllable in-memory doubles.

    The consumer looks at what the detector has produced and returns exactly
    one ACK for each config command. That mirrors the protocol the detector is
    written against without hiding the command traffic from the test.
    """
    backend = JustBinItBackend()
    acked_ids = set()

    def poll_hook(_consumer, timeout_ms=0):
        del timeout_ms
        for command in _commands(backend):
            if command["cmd"] != "config" or command["msg_id"] in acked_ids:
                continue
            acked_ids.add(command["msg_id"])
            return json.dumps({"msg_id": command["msg_id"], "response": "ACK"}).encode(
                "utf-8"
            )
        return None

    consumer = StubKafkaConsumer(poll_hook=poll_hook)
    monkeypatch.setattr(just_bin_it, "KafkaSubscriber", backend.subscribe)
    monkeypatch.setattr(just_bin_it.KafkaProducer, "create", lambda *a, **k: backend)
    monkeypatch.setattr(just_bin_it.KafkaConsumer, "create", lambda *a, **k: consumer)
    monkeypatch.setattr(status_handler, "KafkaSubscriber", StubKafkaSubscriber)
    publisher = threading.Thread(target=backend.run, daemon=True)
    publisher.start()
    try:
        yield backend
    finally:
        backend.stop.set()
        publisher.join(timeout=1)
        assert not publisher.is_alive()


def test_just_bin_it_count_with_timer_preset(session, jbi_backend):
    """A timer-only count sends a config with a stop time and no stop command."""
    jbi_backend.totals = {"image_1": 7, "image_2": 3}
    with loaded_setup(session, "ess_just_bin_it_count_scan"):
        set_detectors(session, "jbi_detector")
        count(t=COUNT_TIMER_PRESET_SECONDS)
        (config,) = _commands(jbi_backend)
        assert config["cmd"] == "config"
        assert config["stop"] - config["start"] == int(
            COUNT_TIMER_PRESET_SECONDS * 1000
        )
        assert session.getDevice("image_1").read()[0] == 7
        assert session.getDevice("image_2").read()[0] == 3


def test_just_bin_it_count_with_explicit_channel_preset(session, jbi_backend):
    """A channel preset makes that image the soft controller; a stop ends the job."""
    jbi_backend.totals = {"image_1": EXPLICIT_IMAGE_PRESET}
    with loaded_setup(session, "ess_just_bin_it_count_scan"):
        set_detectors(session, "jbi_detector")
        count(image_1=EXPLICIT_IMAGE_PRESET)
        assert session.getDevice("image_1").read()[0] == EXPLICIT_IMAGE_PRESET
        assert [c["cmd"] for c in _commands(jbi_backend)] == ["config", "stop"]


def test_just_bin_it_scan_across_two_points(session, jbi_backend):
    """A two-point scan sends two configs with different ids and no stops."""
    with loaded_setup(session, "ess_just_bin_it_count_scan"):
        set_detectors(session, "jbi_detector")
        axis = session.getDevice("axis")
        scan(axis, 0, 1, 2, t=COUNT_TIMER_PRESET_SECONDS)
        configs = _commands(jbi_backend)
        assert [c["cmd"] for c in configs] == ["config", "config"]
        assert configs[0]["msg_id"] != configs[1]["msg_id"]
        assert {h["id"] for h in configs[0]["histograms"]}.isdisjoint(
            h["id"] for h in configs[1]["histograms"]
        )
