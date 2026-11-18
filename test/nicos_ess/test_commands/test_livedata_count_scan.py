"""Count/scan regressions using serialized device-topic data and fake Kafka I/O."""

import json
import threading
import time

import numpy as np
import pytest

pytest.importorskip("streaming_data_types")

from streaming_data_types.dataarray_da00 import Variable, serialise_da00

from nicos.commands.measure import count
from nicos.commands.scan import scan
from nicos.core import UsageError
from nicos_ess.devices.datasources import livedata
from nicos_ess.utilities.frame_views import axis
from nicos_ess.utilities.live_frame import decode
from test.nicos_ess.command_helpers import loaded_setup, scan_positions, set_detectors
from test.nicos_ess.test_devices.doubles import (
    StubKafkaConsumer,
    StubKafkaMessage,
    StubKafkaProducer,
    StubKafkaSubscriber,
)

session_setup = None
COUNT_TIMER_PRESET_SECONDS = 0.05
CHANNEL_PRESET_TOTAL = 5


class LiveDataBackend(StubKafkaProducer):
    """Publish a standing total, then a distinct value for each workflow reset."""

    def __init__(self):
        super().__init__()
        self.subscribers = []
        # esslivedata answers each reset with an ACK. A poll waits a little like
        # a real Kafka poll.
        self.answers = StubKafkaConsumer(poll_hook=lambda *a, **k: time.sleep(0.01))
        self.start_ns = time.time_ns() - 100 * 10**9
        self.total = 900000
        self.sources = ("monitor", "monitor2")
        self.stop = threading.Event()
        self.sent = threading.Event()
        self.lock = threading.RLock()
        # Signal per time-of-flight bin. With None the backend sends a total.
        self.histogram = None

    def subscribe(self, brokers):
        subscriber = StubKafkaSubscriber(brokers)
        self.subscribers.append(subscriber)
        return subscriber

    def produce(self, topic, message, **kwargs):
        with self.lock:
            super().produce(topic, message, **kwargs)
            command = json.loads(message)
            assert command["action"] == "reset"
            self.start_ns = time.time_ns()
            ack = dict(message_id=command["message_id"], response="ACK")
            self.answers.queue_record(
                StubKafkaMessage(
                    json.dumps(ack).encode(),
                    topic="livedata_responses",
                    timestamp=(1, self.start_ns // 10**6),
                )
            )
            self.total = CHANNEL_PRESET_TOTAL * len(self.messages)

    def variables(self):
        stamps = [
            Variable(name=name, data=np.asarray(ns), axes=[], unit="ns")
            for name, ns in (("start_time", self.start_ns), ("time", time.time_ns()))
        ]
        if self.histogram is None:
            return [Variable(name="signal", data=np.asarray(self.total)), *stamps]
        edges = np.linspace(0.0, 71000.0, len(self.histogram) + 1)
        return [
            Variable(name="signal", data=np.asarray(self.histogram), axes=["tof"]),
            Variable(name="tof", data=edges, axes=["tof"], unit="us"),
            *stamps,
        ]

    def run(self):
        while not self.stop.wait(0.005):
            with self.lock:
                messages = []
                at = (1, time.time_ns() // 10**6)
                for name in self.sources:
                    raw = serialise_da00(
                        source_name=name, timestamp_ns=0, data=self.variables()
                    )
                    messages.append((at, raw))
                for subscriber in self.subscribers:
                    if not subscriber.closed:
                        subscriber.emit_messages(messages)
                        if subscriber.messages_callback:
                            self.sent.set()


@pytest.fixture
def livedata_backend(monkeypatch):
    backend = LiveDataBackend()
    # Replace only the Kafka transport; messages still pass through collector routing.
    monkeypatch.setattr(livedata, "KafkaSubscriber", backend.subscribe)
    # Deliver reset commands to the controllable fake backend instead of a broker.
    monkeypatch.setattr(livedata.KafkaProducer, "create", lambda *a, **k: backend)
    monkeypatch.setattr(
        livedata.KafkaConsumer, "create", lambda *a, **k: backend.answers
    )
    publisher = threading.Thread(target=backend.run, daemon=True)
    publisher.start()
    try:
        yield backend
    finally:
        backend.stop.set()
        publisher.join(timeout=1)
        assert not publisher.is_alive()


def test_livedata_count_with_timer_preset(session, livedata_backend):
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        result = count(t=COUNT_TIMER_PRESET_SECONDS)
        assert result[1:] == [5, 5]
        assert session.getDevice("channel_1").running is False
        assert len(livedata_backend.messages) == 1


def test_livedata_count_with_explicit_channel_preset(session, livedata_backend):
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        result = count(channel_1=CHANNEL_PRESET_TOTAL)
        assert result[1:] == [5, 5]
        assert not session.getDevice("channel_1").running


def test_livedata_scan_across_two_points(session, livedata_backend):
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        axis = session.getDevice("axis")
        scan(axis, 0, 1, 2, t=COUNT_TIMER_PRESET_SECONDS)
        dataset = session.experiment.data.getLastScans()[-1]
        assert scan_positions(dataset) == [0.0, 1.0]
        assert [point[-2:] for point in dataset.detvaluelists] == [[5, 5], [10, 10]]
        assert len(livedata_backend.messages) == 2


@pytest.mark.parametrize(
    "sources, expected", [(("monitor",), [5, 0]), (("monitor2",), [0, 5]), ((), [0, 0])]
)
def test_silent_channel_reads_zero_without_blocking_the_count(
    session, livedata_backend, sources, expected
):
    livedata_backend.sources = sources
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        started = time.monotonic()
        result = count(t=COUNT_TIMER_PRESET_SECONDS)
        # finish() waits finish_timeout, 10 s, only for a channel that sends data.
        assert time.monotonic() - started < 5
        assert result[1:] == expected
        assert not session.getDevice("channel_1").running


def test_channel_that_goes_silent_reads_zero(session, livedata_backend):
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        # Establish real idle data before interrupting the fake data transport.
        assert livedata_backend.sent.wait(1)
        with livedata_backend.lock:
            livedata_backend.sources = ()
        result = count(t=COUNT_TIMER_PRESET_SECONDS)
        assert result[1:] == [0, 0]


@pytest.mark.parametrize(
    "detectors", [["channel_1"], ["livedata_collector", "channel_1"]]
)
def test_counting_a_channel_directly_is_a_usage_error(
    session, livedata_backend, detectors
):
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, *detectors)
        with pytest.raises(UsageError, match="cannot be used as a detector"):
            count(t=COUNT_TIMER_PRESET_SECONDS)


def test_a_histogram_reaches_clients_with_its_axis(
    session, livedata_backend, monkeypatch
):
    received = []

    def update_live_data(parameters, databuffers, labelbuffers):
        labels = [bytes(b) for b in labelbuffers]
        for desc, buf in zip(parameters["datadescs"], databuffers, strict=True):
            received.append((parameters["det"], decode(desc, bytes(buf), labels)))

    monkeypatch.setattr(session, "updateLiveData", update_live_data)
    livedata_backend.histogram = [1.0, 4.0, 9.0]
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        count(t=COUNT_TIMER_PRESET_SECONDS)

    assert {det for det, _frame in received} == {"livedata_collector"}
    _det, frame = received[-1]
    assert frame.data.tolist() == [1.0, 4.0, 9.0]
    tof = axis(frame, "tof")
    assert (tof.is_edges, tof.unit, tof.values[-1]) == (True, "us", 71000.0)
    assert frame.name == "channel_2"
