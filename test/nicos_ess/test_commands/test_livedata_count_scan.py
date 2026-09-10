"""Count/scan regressions using serialized device-topic data and fake Kafka I/O."""

import json
import threading

import numpy as np
import pytest

pytest.importorskip("streaming_data_types")

from streaming_data_types.dataarray_da00 import Variable, serialise_da00

from nicos.commands.measure import count
from nicos.commands.scan import scan
from nicos.core import CommunicationError
from nicos_ess.devices.datasources import livedata
from test.nicos_ess.command_helpers import loaded_setup, scan_positions, set_detectors
from test.nicos_ess.test_devices.doubles import StubKafkaProducer, StubKafkaSubscriber

session_setup = None
COUNT_TIMER_PRESET_SECONDS = 0.05
CHANNEL_PRESET_TOTAL = 5


class LiveDataBackend(StubKafkaProducer):
    """Publish a standing total, then a distinct value for each workflow reset."""

    def __init__(self):
        super().__init__()
        self.subscribers = []
        self.generation = 111
        self.total = 900000
        self.publish = True
        self.stop = threading.Event()
        self.sent = threading.Event()
        self.lock = threading.RLock()

    def subscribe(self, brokers):
        subscriber = StubKafkaSubscriber(brokers)
        self.subscribers.append(subscriber)
        return subscriber

    def produce(self, topic, message, **kwargs):
        with self.lock:
            super().produce(topic, message, **kwargs)
            command = json.loads(message)
            assert command["action"] == "reset"
            self.generation += 1
            self.total = CHANNEL_PRESET_TOTAL * len(self.messages)

    def run(self):
        while not self.stop.wait(0.005):
            with self.lock:
                if not self.publish:
                    continue
                messages = []
                for name in ("monitor", "monitor2"):
                    raw = serialise_da00(
                        source_name=name,
                        timestamp_ns=0,
                        data=[
                            Variable(
                                name="signal",
                                data=np.asarray(self.total),
                                shape=(),
                                axes=[],
                            ),
                            Variable(
                                name="start_time",
                                data=np.asarray(self.generation),
                                shape=(),
                                axes=[],
                            ),
                        ],
                    )
                    messages.append(((1, 0), raw))
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


def test_timer_cannot_record_zero_when_post_reset_data_is_missing(
    session, livedata_backend
):
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        # Establish real idle data before interrupting the fake data transport.
        assert livedata_backend.sent.wait(1)
        with livedata_backend.lock:
            livedata_backend.publish = False
        with pytest.raises(CommunicationError, match="No post-reset data"):
            count(t=COUNT_TIMER_PRESET_SECONDS)
        assert not session.getDevice("channel_1").running
