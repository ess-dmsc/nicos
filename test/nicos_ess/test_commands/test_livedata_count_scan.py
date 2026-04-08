"""Command-level tests for the livedata collector/data-channel integration.

The tests drive the public `count()` and `scan()` commands while faking the
minimal DA00 traffic needed to make the collector and channels progress.
"""

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

# The command tests load their own explicit setup and should not inherit a
# preselected detector list from any session setup.
session_setup = None
COUNT_TIMER_PRESET_SECONDS = 0.02
CHANNEL_PRESET_TOTAL = 5


def _publish_livedata_when_running(channel, total):
    """Push one DA00 update directly into a running channel.

    This bypasses Kafka transport on purpose: command tests are about preset
    routing and count-loop behaviour, while the device harness tests already
    cover the collector/channel DA00 decoding path in detail.
    """
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
    """Replace Kafka plumbing with stubs and make prepare-time sleeps instant."""
    producer = StubKafkaProducer()
    monkeypatch.setattr(livedata, "KafkaSubscriber", StubKafkaSubscriber)
    monkeypatch.setattr(livedata.KafkaProducer, "create", lambda *a, **k: producer)
    monkeypatch.setattr(livedata, "sleep", lambda *_: None)
    return producer


def test_livedata_count_with_timer_preset(session, livedata_backend):
    """Timer-controlled counts should leave the channel stopped afterwards."""
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        count(t=COUNT_TIMER_PRESET_SECONDS)
        assert session.getDevice("channel_1").running is False


def test_livedata_count_with_explicit_channel_preset(session, livedata_backend):
    """A channel preset should turn that channel into the soft controller.

    The injected DA00 message carries a single-bin signal with the target
    total, so the final readback is easy to understand from the assertion.
    """
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        channel = session.getDevice("channel_1")
        publisher = threading.Thread(
            target=_publish_livedata_when_running,
            args=(channel, CHANNEL_PRESET_TOTAL),
            daemon=True,
        )
        publisher.start()
        count(channel_1=CHANNEL_PRESET_TOTAL)
        publisher.join(timeout=1)
        assert not publisher.is_alive()
        assert channel.read()[0] == CHANNEL_PRESET_TOTAL


def test_livedata_scan_across_two_points(session, livedata_backend):
    """A two-point scan should record exactly the two requested motor positions."""
    with loaded_setup(session, "ess_livedata_count_scan"):
        set_detectors(session, "livedata_collector")
        axis = session.getDevice("axis")
        scan(axis, 0, 1, 2, t=COUNT_TIMER_PRESET_SECONDS)
        dataset = session.experiment.data.getLastScans()[-1]
        assert scan_positions(dataset) == [0.0, 1.0]
