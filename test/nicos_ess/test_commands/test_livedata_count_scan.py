import json
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("streaming_data_types")

from nicos.commands.measure import count
from nicos.commands.scan import scan

from nicos_ess.devices.datasources import livedata

from test.nicos_ess.command_helpers import (
    loaded_setup,
    scan_positions,
    set_detectors,
    wait_until,
)
from test.nicos_ess.test_devices.doubles import (
    StubKafkaProducer,
    StubKafkaSubscriber,
)

session_setup = None


def _publish_livedata_when_running(channel, total):
    assert wait_until(lambda: channel.running)
    source_name = json.dumps(
        {
            "workflow_id": {
                "instrument": "test",
                "namespace": "data_reduction",
                "name": "monitor_data",
                "version": 1,
            },
            "job_id": {"source_name": "monitor", "job_number": "job-1"},
            "output_name": "current",
        }
    )
    signal = SimpleNamespace(
        name="signal",
        data=np.asarray([total], dtype=np.int32),
        axes=["bin_edges"],
        label="Counts",
        unit="events",
    )
    edges = SimpleNamespace(
        name="bin_edges",
        data=np.asarray([0.0, 1.0], dtype=np.float64),
        axes=["bin_edges"],
        unit="",
    )
    channel.update_data_from_da00(
        SimpleNamespace(source_name=source_name, data=[signal, edges]),
        int(time.time() * 1e9),
    )


@pytest.fixture
def livedata_backend(monkeypatch):
    producer = StubKafkaProducer()
    monkeypatch.setattr(livedata, "KafkaSubscriber", StubKafkaSubscriber)
    monkeypatch.setattr(livedata.KafkaProducer, "create", lambda *a, **k: producer)
    monkeypatch.setattr(livedata, "sleep", lambda *_: None)
    return producer


def test_livedata_count_with_timer_preset(session, livedata_backend):
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        count(t=0.02)
        assert session.getDevice("channel_1").running is False


def test_livedata_count_with_explicit_channel_preset(session, livedata_backend):
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        channel = session.getDevice("channel_1")
        publisher = threading.Thread(
            target=_publish_livedata_when_running, args=(channel, 5), daemon=True
        )
        publisher.start()
        count(channel_1=5)
        publisher.join(timeout=1)
        assert not publisher.is_alive()
        assert channel.read()[0] == 5


def test_livedata_scan_across_two_points(session, livedata_backend):
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        axis = session.getDevice("axis")
        scan(axis, 0, 1, 2, t=0.02)
        dataset = session.experiment.data.getLastScans()[-1]
        assert scan_positions(dataset) == [0.0, 1.0]
