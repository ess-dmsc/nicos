import json
import threading
import time
from dataclasses import asdict
from types import SimpleNamespace

import numpy as np
import pytest

from nicos.core import ArrayDesc
from nicos.core.constants import FINAL

from nicos_ess.devices.datasources import livedata
from nicos_ess.devices.datasources.livedata_utils import JobId, ResultKey, WorkflowId
from test.nicos_ess.test_devices.doubles import (
    patch_kafka_stubs,
)


WORKFLOW_ID = WorkflowId(
    instrument="dummy",
    namespace="detector_data",
    name="panel_0_xy",
    version=1,
)
JOB_ID = JobId(source_name="panel_0", job_number="job-1")
OUTPUT_NAME = "current"
SELECTOR = f"{WORKFLOW_ID}@{JOB_ID.source_name}#{JOB_ID.job_number}/{OUTPUT_NAME}"
RESULT_KEY = ResultKey(
    workflow_id=WORKFLOW_ID,
    job_id=JOB_ID,
    output_name=OUTPUT_NAME,
)
TIMESTAMP_NS = 123456789


@pytest.fixture
def kafka_stubs(monkeypatch):
    patch_kafka_stubs(monkeypatch, livedata)
    monkeypatch.setattr(livedata, "sleep", lambda *_args, **_kwargs: None)


@pytest.fixture
def live_data_updates(daemon_device_harness):
    updates = []
    daemon_device_harness.session.updateLiveData = (
        lambda parameters, databuffer, labelbuffers: updates.append(
            {
                "parameters": parameters,
                "databuffer": databuffer,
                "labelbuffers": labelbuffers,
            }
        )
    )
    return updates


def create_channel(daemon_device_harness):
    return daemon_device_harness.create_master(
        livedata.DataChannel,
        name="livedata_channel",
        selector=SELECTOR,
        type="counter",
    )


def create_collector(daemon_device_harness, name, counters):
    return daemon_device_harness.create_master(
        livedata.LiveDataCollector,
        name=name,
        brokers=["localhost:9092"],
        data_topics=["livedata"],
        status_topics=[],
        responses_topics=[],
        commands_topic="",
        counters=counters,
    )


def create_multi_channel_collector(daemon_device_harness):
    channels = [
        daemon_device_harness.create_master(
            livedata.DataChannel,
            name=name,
            selector=SELECTOR,
            type="counter",
        )
        for name in ("livedata_primary", "livedata_secondary", "livedata_roi")
    ]
    collector = create_collector(
        daemon_device_harness,
        name="livedata_collector",
        counters=[channel.name for channel in channels],
    )
    return channels, collector


def make_da00_message():
    return SimpleNamespace(
        source_name=json.dumps(
            {
                "workflow_id": asdict(WORKFLOW_ID),
                "job_id": asdict(JOB_ID),
                "output_name": OUTPUT_NAME,
            }
        ),
        data=[
            SimpleNamespace(
                name="signal",
                data=np.array([1, 2, 3], dtype=np.int32),
                axes=["tof"],
                unit="counts",
                label="Detector signal",
            ),
            SimpleNamespace(
                name="tof",
                data=np.array([0.0, 1.0, 2.0], dtype=np.float64),
                axes=["tof"],
                unit="ms",
                label="TOF",
            ),
        ],
    )


class TestDataChannelHarness:
    def test_array_info_returns_tuple_and_read_results_include_array(
        self, daemon_device_harness, kafka_stubs, live_data_updates
    ):
        del kafka_stubs
        channel = create_channel(daemon_device_harness)

        channel.start()
        channel.update_data_from_da00(make_da00_message(), TIMESTAMP_NS)
        info = channel.arrayInfo()
        scalars, arrays = channel.readResults(FINAL)

        assert isinstance(info, tuple)
        assert len(info) == 1
        assert isinstance(info[0], ArrayDesc)
        assert scalars == [6]
        assert len(arrays) == 1
        assert arrays[0].shape == info[0].shape
        assert live_data_updates[0]["parameters"]["det"] == "livedata_channel"


class TestLiveDataCollectorHarness:
    def test_routes_da00_and_completes_on_scalar_preset(
        self, daemon_device_harness, kafka_stubs, live_data_updates
    ):
        del kafka_stubs
        channel = create_channel(daemon_device_harness)
        collector = create_collector(
            daemon_device_harness,
            name="livedata_collector",
            counters=[channel.name],
        )

        collector.setPreset(n=6)
        collector.prepare()
        collector.start()
        collector._dispatch_to_channels(TIMESTAMP_NS, RESULT_KEY, make_da00_message())
        scalars, arrays = collector.readResults(FINAL)

        assert collector.isCompleted() is True
        assert scalars == [6]
        assert arrays == []
        assert live_data_updates[0]["parameters"]["det"] == "livedata_channel"

    def test_uses_first_counter_for_n_and_named_channel_explicitly(
        self, daemon_device_harness, kafka_stubs
    ):
        del kafka_stubs
        channels, collector = create_multi_channel_collector(daemon_device_harness)
        primary, secondary, _roi = channels

        collector.setPreset(n=6)

        assert tuple(ch.name for ch in collector._controlchannels) == (
            "livedata_primary",
        )
        assert collector._channel_presets == {primary: [("n", 6)]}

        collector.setPreset(livedata_secondary=4)

        assert tuple(ch.name for ch in collector._controlchannels) == (
            "livedata_secondary",
        )
        assert collector._channel_presets == {secondary: [("livedata_secondary", 4)]}

    def test_pause_reports_unsupported_and_resume_is_noop(
        self, daemon_device_harness, kafka_stubs
    ):
        del kafka_stubs
        channel = create_channel(daemon_device_harness)
        collector = create_collector(
            daemon_device_harness,
            name="livedata_collector",
            counters=[channel.name],
        )

        collector.setPreset(n=6)
        collector.prepare()
        collector.start()

        assert collector.pause() is False
        collector.resume()

    def test_completion_waits_for_full_da00_dispatch_before_reading_results(
        self, daemon_device_harness, kafka_stubs, monkeypatch
    ):
        del kafka_stubs
        channels, collector = create_multi_channel_collector(daemon_device_harness)
        primary, _secondary, _roi = channels
        collector.setPreset(n=6)
        collector.prepare()
        collector.start()

        controller_updated = threading.Event()
        release_controller = threading.Event()
        original_update = livedata.DataChannel.update_data_from_da00

        def delayed_primary_update(channel, da00_msg, timestamp_ns):
            original_update(channel, da00_msg, timestamp_ns)
            if channel is primary:
                controller_updated.set()
                release_controller.wait(timeout=1.0)

        monkeypatch.setattr(
            livedata.DataChannel,
            "update_data_from_da00",
            delayed_primary_update,
        )

        dispatch_thread = threading.Thread(
            target=collector._dispatch_to_channels,
            args=(TIMESTAMP_NS, RESULT_KEY, make_da00_message()),
            daemon=True,
        )
        dispatch_thread.start()
        assert controller_updated.wait(timeout=1.0)

        completion_result = []

        def check_completion():
            completion_result.append(collector.isCompleted())

        completion_thread = threading.Thread(target=check_completion, daemon=True)
        completion_thread.start()
        time.sleep(0.05)

        assert completion_thread.is_alive()

        release_controller.set()
        dispatch_thread.join(timeout=1.0)
        completion_thread.join(timeout=1.0)

        assert completion_result == [True]
        assert collector.read() == [6, 6, 6]
