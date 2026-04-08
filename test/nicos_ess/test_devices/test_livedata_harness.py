import json
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("streaming_data_types")

from streaming_data_types.dataarray_da00 import Variable, serialise_da00

from nicos import session as nicos_session

from nicos_ess.devices.datasources import livedata
from nicos_ess.devices.datasources.livedata_utils import JobId, WorkflowId
from nicos_ess.devices.timer import TimerChannel

from test.nicos_ess.test_devices.doubles import (
    StubKafkaProducer,
    StubKafkaSubscriber,
)

_SOURCE_NAME = json.dumps(
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


@pytest.fixture
def livedata_stubs(monkeypatch):
    producer = StubKafkaProducer()
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


def _make_da00(source_name, variables):
    return SimpleNamespace(source_name=source_name, data=variables)


def _var(name, data, axes=None, unit="", label=None):
    ns = SimpleNamespace(name=name, data=np.asarray(data), unit=unit)
    if axes is not None:
        ns.axes = axes
    if label is not None:
        ns.label = label
    return ns


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
        collector._registry.note_output(
            workflow, JobId("monitor", "job-1"), "current"
        )
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

        payload = json.loads(
            livedata_stubs.messages[0]["message"].decode("utf-8")
        )
        assert payload["action"] == "reset"
        assert payload["job_id"] == {
            "source_name": "monitor",
            "job_number": "job-1",
        }

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

        raw = serialise_da00(
            source_name=_SOURCE_NAME,
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


class TestDataChannelDimensionHandling:
    """Regression tests for DA00 signals of various dimensionalities."""

    @pytest.fixture(autouse=True)
    def setup_channel(self, daemon_device_harness, livedata_stubs, monkeypatch):
        self.captured = []
        self.channel = _create_channel(daemon_device_harness)
        _create_collector(daemon_device_harness, ["channel"])
        monkeypatch.setattr(
            nicos_session,
            "updateLiveData",
            lambda parameters, databuffer, labelbuffers: self.captured.append(
                (parameters, databuffer, labelbuffers)
            ),
        )
        self.channel.start()

    def _send(self, variables):
        da00 = _make_da00(_SOURCE_NAME, variables)
        self.channel.update_data_from_da00(da00, 123456789)

    def test_scalar_signal(self):
        self._send([_var("signal", 42, axes=["dim0"])])

        assert self.channel.read(0)[0] == 42
        assert self.channel._signal.shape == (1,)

    def test_1d_signal(self):
        self._send([
            _var("signal", [10, 20, 30], axes=["x"]),
            _var("x", [0.0, 1.0, 2.0, 3.0], axes=["x"]),
        ])

        assert self.channel.read(0)[0] == 60
        assert self.channel._signal.shape == (3,)

    def test_2d_signal(self):
        data = np.arange(6, dtype=np.float64).reshape(2, 3)
        self._send([
            _var("signal", data, axes=["y", "x"]),
            _var("x", [0.0, 1.0, 2.0, 3.0], axes=["x"]),
            _var("y", [0.0, 1.0, 2.0], axes=["y"]),
        ])

        assert self.channel.read(0)[0] == 15
        assert self.channel._signal.shape == (2, 3)

    def test_no_signal_variable_is_ignored(self):
        self._send([_var("not_signal", [1, 2, 3], axes=["x"])])

        assert self.channel.read(0)[0] == 0
        assert self.channel._signal is None

    def test_consecutive_updates_replace_value(self):
        self._send([_var("signal", [1, 2], axes=["x"])])
        assert self.channel.read(0)[0] == 3

        self._send([_var("signal", [10, 20], axes=["x"])])
        assert self.channel.read(0)[0] == 30

    def test_channel_not_running_ignores_data(self):
        self.channel.running = False
        self._send([_var("signal", [99], axes=["x"])])

        assert self.channel.read(0)[0] == 0
        assert self.channel._signal is None
