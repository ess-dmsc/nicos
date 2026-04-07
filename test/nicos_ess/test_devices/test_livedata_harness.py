import json

import numpy as np
import pytest

pytest.importorskip("streaming_data_types")

from streaming_data_types.dataarray_da00 import Variable, serialise_da00

from nicos import session as nicos_session

from nicos_ess.devices.datasources import livedata
from nicos_ess.devices.datasources.livedata_utils import JobId, WorkflowId
from nicos_ess.devices.timer import TimerChannel

from test.nicos_ess.test_devices.doubles import StubKafkaSubscriber


class RecordingKafkaProducer:
    def __init__(self):
        self.messages = []

    def produce(self, topic, message, **kwargs):
        self.messages.append(
            {
                "topic": topic,
                "message": message,
                "key": kwargs.get("key"),
            }
        )
        callback = kwargs.get("on_delivery_callback")
        if callback:
            callback(None, object())


@pytest.fixture
def livedata_stubs(monkeypatch):
    producer = RecordingKafkaProducer()
    monkeypatch.setattr(livedata, "KafkaSubscriber", StubKafkaSubscriber)
    monkeypatch.setattr(livedata.KafkaProducer, "create", lambda *a, **k: producer)
    monkeypatch.setattr(livedata, "sleep", lambda *_: None)
    return producer


def _create_channel(daemon_device_harness, name="channel"):
    return daemon_device_harness.create_master(
        livedata.DataChannel,
        name=name,
        selector="test/data_reduction/monitor_data/1@monitor/current",
        type="counter",
    )


def _create_collector(daemon_device_harness, channel_names):
    daemon_device_harness.create_master(
        TimerChannel,
        name="timer",
        update_interval=0.01,
    )
    return daemon_device_harness.create_master(
        livedata.LiveDataCollector,
        name="livedata_collector",
        brokers=["localhost:9092"],
        data_topics=["livedata_data"],
        commands_topic="livedata_commands",
        others=channel_names,
        timers=["timer"],
    )


class TestLiveDataHarness:
    def test_selector_move_updates_channel_selector(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        workflow = WorkflowId("test", "data_reduction", "monitor_data", 1)

        collector._registry.jobinfo_from_status(
            workflow,
            job_source_name="monitor",
            job_number="job-1",
            state="active",
        )
        collector._registry.note_output(workflow, JobId("monitor", "job-1"), "current")
        mapping = collector.get_current_mapping()
        label, selector = next(iter(mapping.items()))

        channel.mapping = mapping
        channel.move(label)

        assert channel.selector == selector

    def test_prepare_keeps_backend_reset_behavior(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])

        def _prime_and_prepare():
            collector._registry.jobinfo_from_status(
                WorkflowId("test", "data_reduction", "monitor_data", 1),
                job_source_name="monitor",
                job_number="job-1",
                state="active",
            )
            channel.prepare()

        _prime_and_prepare()

        payload = json.loads(livedata_stubs.messages[0]["message"].decode("utf-8"))
        assert payload["action"] == "reset"
        assert payload["job_id"] == {"source_name": "monitor", "job_number": "job-1"}

    def test_da00_routing_updates_scalar_value_and_live_payload(
        self, daemon_device_harness, livedata_stubs, monkeypatch
    ):
        captured = []
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])

        monkeypatch.setattr(
            nicos_session,
            "updateLiveData",
            lambda parameters, databuffer, labelbuffers: captured.append(
                (parameters, databuffer, labelbuffers)
            ),
        )
        channel.start()

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
        raw = serialise_da00(
            source_name=source_name,
            timestamp_ns=123456789,
            data=[
                Variable(
                    name="signal",
                    data=np.asarray([2, 3], dtype=np.int32),
                    shape=(2,),
                    axes=["bin_edges"],
                    source="monitor",
                ),
                Variable(
                    name="bin_edges",
                    data=np.asarray([0.0, 1.0, 2.0], dtype=np.float64),
                    shape=(3,),
                    axes=["bin_edges"],
                    source="monitor",
                ),
            ],
        )

        collector._on_data_messages([(123456789, raw)])

        assert channel.read(0)[0] == 5
        assert captured
        assert captured[0][0]["det"] == "channel"
