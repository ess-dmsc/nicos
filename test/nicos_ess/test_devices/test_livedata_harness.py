"""Harness tests for the livedata collector and data channels.

The tests make the protocol boundaries explicit:

- the collector owns routing and the workflow reset commands
- channels own array/value updates
- DA00 payloads are injected directly so each test can show exactly which
  input produced the asserted result
"""

import json
import time
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("streaming_data_types")

from streaming_data_types.dataarray_da00 import Variable, serialise_da00
from streaming_data_types.status_x5f2 import serialise_x5f2

from nicos import session as nicos_session
from nicos.core import CommunicationError, status
from nicos_ess.devices.datasources import livedata
from nicos_ess.devices.timer import TimerChannel
from test.nicos_ess.test_devices.doubles import (
    StubKafkaConsumer,
    StubKafkaProducer,
    StubKafkaSubscriber,
)

# On the device topic the DA00 source name is the bare device name.
_SOURCE_NAME = "monitor"


class ResetProducer(StubKafkaProducer):
    error = None
    deliver = True
    fail = False

    def produce(self, topic, message, **kwargs):
        if self.fail:
            raise RuntimeError("Producer unavailable")
        callback = kwargs.pop("on_delivery_callback", None)
        super().produce(topic, message, **kwargs)
        if callback and self.deliver:
            callback(self.error, None)


@pytest.fixture
def livedata_stubs(monkeypatch):
    """Patch livedata Kafka plumbing with explicit in-memory doubles."""
    producer = ResetProducer()
    # Replace Kafka network I/O with an explicitly driven subscriber.
    monkeypatch.setattr(livedata, "KafkaSubscriber", StubKafkaSubscriber)
    # Replace broker delivery with a controllable in-memory transport.
    monkeypatch.setattr(livedata.KafkaProducer, "create", lambda *a, **k: producer)
    # Avoid a real broker connection for heartbeat tests.
    monkeypatch.setattr(
        livedata.KafkaConsumer, "create", lambda *a, **k: StubKafkaConsumer()
    )
    return producer


def _create_channel(daemon_device_harness, name="channel", **config):
    """Create one data channel whose device name matches `_SOURCE_NAME`."""
    return daemon_device_harness.create_master(
        livedata.DataChannel,
        name=name,
        workflow_id="test/monitor_data/1",
        device_name="monitor",
        source_name="monitor",
        type="counter",
        **config,
    )


def _create_collector(
    daemon_device_harness, channel_names, status_topics=(), *, seed=True, timers=True
):
    """Create the collector plus a timer so count/prepare behave like production."""
    daemon_device_harness.create_master(
        TimerChannel,
        name="timer",
        update_interval=0.01,
    )
    collector = daemon_device_harness.create_master(
        livedata.LiveDataCollector,
        name="livedata_collector",
        brokers=["localhost:9092"],
        data_topics=["livedata_nicos_data"],
        commands_topic="livedata_commands",
        status_topics=list(status_topics),
        others=channel_names,
        timers=["timer"] if timers else [],
    )
    if seed:
        _send_data(collector, 500, 111)
    return collector


def _send_data(collector, total, generation):
    data = [Variable(name="signal", data=np.asarray(total), shape=(), axes=[])]
    if generation is not None:
        data.append(
            Variable(name="start_time", data=np.asarray(generation), shape=(), axes=[])
        )
    collector._data_subscriber.emit_messages(
        [((1, 0), serialise_da00(source_name="monitor", timestamp_ns=0, data=data))]
    )


def _job_heartbeat(
    state, nicos_status, error=None, update_interval=1000, source_name="monitor"
):
    """Serialise one x5f2 job heartbeat the way the backend publishes it."""
    return serialise_x5f2(
        software_name="livedata",
        software_version="0.0.0",
        service_id="monitor:job-1",
        host_name="",
        process_id=0,
        update_interval=update_interval,
        status_json=json.dumps(
            {
                "status": nicos_status,
                "message": {
                    "message_type": "job",
                    "state": state,
                    "error": error,
                    "job_id": {"source_name": source_name, "job_number": "job-1"},
                    "workflow_id": "test/monitor_data/1",
                },
            }
        ),
    )


def _make_da00(source_name, variables):
    """Build the minimal DA00-like object the channel update path expects."""
    return SimpleNamespace(source_name=source_name, data=variables)


def _var(name, data, axes=None, unit="", label=None):
    """Create a small variable object for DA00 shape/axis tests."""
    ns = SimpleNamespace(name=name, data=np.asarray(data), unit=unit)
    if axes is not None:
        ns.axes = axes
    if label is not None:
        ns.label = label
    return ns


class TestLiveDataHarness:
    def test_start_sends_workflow_reset(self, daemon_device_harness, livedata_stubs):
        """Starting a count resets the workflow behind the channels."""
        _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])

        collector.prepare()
        collector.start()
        collector.stop()

        payload = json.loads(livedata_stubs.messages[0]["message"].decode("utf-8"))
        assert payload["action"] == "reset"
        assert payload["kind"] == "job_command"
        assert payload["workflow_id"] == "test/monitor_data/1"

    def test_reset_is_sent_once_per_workflow(
        self, daemon_device_harness, livedata_stubs
    ):
        """Channels sharing a workflow are covered by a single reset command."""
        _create_channel(daemon_device_harness, name="channel")
        _create_channel(daemon_device_harness, name="channel_b")
        collector = _create_collector(daemon_device_harness, ["channel", "channel_b"])

        collector.prepare()
        collector.start()
        collector.stop()

        resets = [
            json.loads(m["message"].decode("utf-8")) for m in livedata_stubs.messages
        ]
        assert [r["workflow_id"] for r in resets] == ["test/monitor_data/1"]

    def test_da00_routing_updates_scalar_value_and_live_payload(
        self, daemon_device_harness, livedata_stubs, monkeypatch
    ):
        """Collector routing should update both readback and live-data output."""
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
            source_name="monitor",
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
                Variable(name="start_time", data=np.asarray(111), shape=(), axes=[]),
            ],
        )

        collector._on_data_messages([(123456789, raw)])

        assert channel.read(0)[0] == 5
        assert captured
        # Live data should be attributed to the channel name that matched.
        assert captured[0][0]["det"] == "channel"


class TestResetGate:
    """A count must not pick up the accumulation its reset was meant to clear."""

    def _send(self, channel, total, generation=None):
        variables = [_var("signal", [total], axes=["x"])]
        if generation is not None:
            variables.append(_var("start_time", generation))
        channel.update_data_from_da00(_make_da00(_SOURCE_NAME, variables), 123456789)

    def test_data_from_the_previous_generation_is_ignored(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        self._send(channel, 500, generation=111)
        collector.prepare()
        collector.start()

        self._send(channel, 500, generation=111)

        assert channel.read(0)[0] == 0

    @pytest.mark.parametrize("first, last", [(7, 9), (0, 0)])
    def test_data_from_the_new_generation_is_accepted(
        self, daemon_device_harness, livedata_stubs, first, last
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        self._send(channel, 500, generation=111)
        collector.prepare()
        collector.start()

        self._send(channel, 500, generation=111)
        self._send(channel, first, generation=222)
        self._send(channel, last, generation=222)

        collector.finish()
        assert channel.read(0)[0] == last
        assert channel.status(0)[0] == status.OK

    def test_signals_without_a_generation_fail_the_count(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()

        self._send(channel, 7)

        assert channel.read(0)[0] == 0
        assert channel.status(0) == (status.ERROR, "Missing start_time in data")

    def test_first_count_waits_for_a_baseline_before_sending_reset(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness, data_timeout=0.1)
        collector = _create_collector(daemon_device_harness, ["channel"], seed=False)
        with pytest.raises(CommunicationError, match="No initial data"):
            collector.prepare()
            collector.start()
        assert not livedata_stubs.messages
        assert not channel.running

        _send_data(collector, 900000, 111)
        collector.prepare()
        collector.start()
        _send_data(collector, 900000, 111)
        assert channel.read(0) == [0]
        _send_data(collector, 7, 222)
        assert channel.read(0) == [7]

    def test_unexpected_reset_latches_error_until_next_count(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()
        _send_data(collector, 80, 222)
        _send_data(collector, 3, 333)
        _send_data(collector, 9, 333)
        assert channel.read(0) == [80]
        assert channel.status(0) == (status.ERROR, "Accumulation reset during count")
        collector.stop()
        assert channel.status(0)[0] == status.ERROR

        collector.prepare()
        collector.start()
        _send_data(collector, 12, 444)
        collector.finish()
        assert channel.read(0) == [12]
        assert channel.status(0)[0] == status.OK

    def test_old_generation_cannot_replace_confirmed_data(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()
        _send_data(collector, 7, 222)
        _send_data(collector, 900000, 111)
        assert channel.read(0) == [7]
        assert channel.status(0)[0] == status.BUSY

    def test_finish_without_post_reset_data_fails(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()
        with pytest.raises(CommunicationError, match="No post-reset data"):
            collector.finish()
        assert not channel.running
        assert channel.status(0)[0] == status.ERROR

    @pytest.mark.parametrize("receive_data", [False, True])
    def test_count_fails_when_data_stops_arriving(
        self, daemon_device_harness, livedata_stubs, monkeypatch, receive_data
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()
        if receive_data:
            _send_data(collector, 7, 222)
        now = time.monotonic()
        # Advance elapsed time without waiting through a real acquisition timeout.
        monkeypatch.setattr(
            livedata.time, "monotonic", lambda: now + channel.data_timeout + 1
        )
        collector._data_subscriber.emit_idle()
        assert channel.status() == (status.ERROR, "Timed out waiting for fresh data")

    @pytest.mark.parametrize("failure", ["error", "timeout", "exception"])
    def test_delivery_failure_does_not_start_channels(
        self, daemon_device_harness, livedata_stubs, failure
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        if failure == "error":
            livedata_stubs.error = "Broker rejected reset"
        elif failure == "timeout":
            livedata_stubs.deliver = False
        else:
            livedata_stubs.fail = True
        with pytest.raises(CommunicationError, match="reset"):
            collector.prepare()
            collector.start()
        assert not channel.running
        assert collector.read(0) == [0, 0]


class TestWorkflowHealth:
    """The heartbeat topic answers 'is the workflow behind this device up?'."""

    def _setup(self, daemon_device_harness):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(
            daemon_device_harness, ["channel"], status_topics=["livedata_heartbeat"]
        )
        return channel, collector

    def test_channel_errors_while_no_job_is_heartbeating(
        self, daemon_device_harness, livedata_stubs, monkeypatch
    ):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(
            _job_heartbeat("active", status.OK, source_name="another_monitor")
        )
        assert channel.status(0) == (status.WARN, "Waiting for job heartbeat")
        now = time.monotonic()
        # Skip the initial subscription grace period when no heartbeat ever arrives.
        monkeypatch.setattr(
            livedata.time, "monotonic", lambda: now + collector.status_timeout + 1
        )
        assert channel.status(0)[0] == status.ERROR

    def test_active_job_lets_the_channel_report_its_own_state(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)

        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))

        assert channel.status(0) == channel.curstatus

    def test_job_error_is_reported_as_the_channel_status(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)

        collector._note_job_heartbeat(
            _job_heartbeat("error", status.ERROR, error="workflow blew up")
        )

        assert channel.status(0) == (status.ERROR, "workflow blew up")

    def test_stopped_job_is_dropped(self, daemon_device_harness, livedata_stubs):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))

        collector._note_job_heartbeat(_job_heartbeat("stopped", status.OK))

        assert channel.status(0)[0] == status.ERROR

    def test_heartbeat_expires_after_the_grace_period(
        self, daemon_device_harness, livedata_stubs, monkeypatch
    ):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))
        assert channel.status(0) == channel.curstatus

        now = time.monotonic()
        expiry = 1 + collector.status_timeout + 1
        # Advance the heartbeat deadline without a real grace-period wait.
        monkeypatch.setattr(livedata.time, "monotonic", lambda: now + expiry)

        assert channel.status(0)[0] == status.ERROR

    def test_status_topics_unset_means_no_health_opinion(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        _create_collector(daemon_device_harness, ["channel"])

        assert channel.status(0) == channel.curstatus

    def test_health_change_is_pushed_to_the_cache(
        self, daemon_device_harness, livedata_stubs
    ):
        """A cached status() must see a workflow dying without being forced."""
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))
        collector._publish_health_changes()
        assert channel.status()[0] == status.OK

        collector._note_job_heartbeat(
            _job_heartbeat("error", status.ERROR, error="workflow blew up")
        )
        collector._publish_health_changes()

        assert channel.status() == (status.ERROR, "workflow blew up")

    def test_sibling_job_does_not_hide_stopped_source(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))
        collector._note_job_heartbeat(
            _job_heartbeat("active", status.OK, source_name="another_monitor")
        )
        collector._note_job_heartbeat(_job_heartbeat("stopped", status.OK))
        assert channel.status(0)[0] == status.ERROR

    def test_sibling_error_does_not_fail_healthy_source(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))
        collector._note_job_heartbeat(
            _job_heartbeat("error", status.ERROR, source_name="another_monitor")
        )
        assert channel.status(0)[0] == status.OK

    def test_sibling_heartbeat_does_not_hide_source_expiry(
        self, daemon_device_harness, livedata_stubs, monkeypatch
    ):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))
        now = time.monotonic()
        # Expire only the monitored source while a sibling continues heartbeating.
        monkeypatch.setattr(
            livedata.time, "monotonic", lambda: now + 1 + collector.status_timeout + 1
        )
        collector._note_job_heartbeat(
            _job_heartbeat("active", status.OK, source_name="another_monitor")
        )
        assert channel.status(0)[0] == status.ERROR

    def test_warning_does_not_complete_soft_count(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(
            daemon_device_harness, ["channel"], ["livedata_heartbeat"], timers=False
        )
        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))
        collector.start(channel=100)
        _send_data(collector, 7, 222)
        collector._note_job_heartbeat(_job_heartbeat("warning", status.WARN))
        assert not collector.isCompleted()
        assert channel.status(0) == (status.BUSY, "warning")
        _send_data(collector, 100, 222)
        assert collector.isCompleted()
        collector.finish()

    def test_shutdown_closes_both_transports(
        self, daemon_device_harness, livedata_stubs
    ):
        _, collector = self._setup(daemon_device_harness)
        data = collector._data_subscriber
        heartbeat = collector._status_consumer
        collector.shutdown()
        assert data.closed
        assert heartbeat.closed


class TestDataChannelDimensionHandling:
    """Regression tests for DA00 signals of various dimensionalities."""

    @pytest.fixture(autouse=True)
    def setup_channel(self, daemon_device_harness, livedata_stubs, monkeypatch):
        """Create one started channel and capture each live-data publish.

        The fixture starts the channel once up front so the per-test assertions
        can stay about signal-shape handling instead of count lifecycle.
        """
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
        """Inject one DA00 payload directly into the channel update path."""
        variables = [*variables, _var("start_time", 111)]
        da00 = _make_da00(_SOURCE_NAME, variables)
        self.channel.update_data_from_da00(da00, 123456789)

    def test_scalar_signal(self):
        """Scalar signals are normalised into a one-element 1-D array."""
        self._send([_var("signal", 42, axes=["dim0"])])

        assert self.channel.read(0)[0] == 42
        assert self.channel._signal.shape == (1,)

    def test_1d_signal(self):
        """A 1-D signal should keep its natural shape and summed readback."""
        self._send(
            [
                _var("signal", [10, 20, 30], axes=["x"]),
                _var("x", [0.0, 1.0, 2.0, 3.0], axes=["x"]),
            ]
        )

        assert self.channel.read(0)[0] == 60
        assert self.channel._signal.shape == (3,)

    def test_2d_signal(self):
        """A 2-D signal should preserve both dimensions."""
        data = np.arange(6, dtype=np.float64).reshape(2, 3)
        self._send(
            [
                _var("signal", data, axes=["y", "x"]),
                _var("x", [0.0, 1.0, 2.0, 3.0], axes=["x"]),
                _var("y", [0.0, 1.0, 2.0], axes=["y"]),
            ]
        )

        assert self.channel.read(0)[0] == 15
        assert self.channel._signal.shape == (2, 3)

    @pytest.mark.parametrize(
        "shape, axes, expected_shape",
        [
            ((2, 3, 4), ["blade", "wire", "strip"], (2, 12)),
            ((2, 3, 4, 5), ["a", "b", "c", "d"], (4, 5)),
        ],
    )
    def test_existing_nd_views(self, shape, axes, expected_shape):
        data = np.ones(shape, dtype=np.int32)
        self._send([_var("signal", data, axes=axes)])
        assert self.channel.read(0) == [data.size]
        assert self.channel.arrayInfo().shape == expected_shape
        assert self.captured[0][0]["datadescs"][0]["shape"] == expected_shape

    def test_no_signal_variable_is_ignored(self):
        """Payloads without a `signal` variable should leave the channel unchanged."""
        self._send([_var("not_signal", [1, 2, 3], axes=["x"])])

        assert self.channel.read(0)[0] == 0
        assert self.channel._signal is None

    def test_consecutive_updates_replace_value(self):
        """Later DA00 updates should replace, not accumulate, the cached signal."""
        self._send([_var("signal", [1, 2], axes=["x"])])
        assert self.channel.read(0)[0] == 3

        self._send([_var("signal", [10, 20], axes=["x"])])
        assert self.channel.read(0)[0] == 30

    def test_channel_not_running_ignores_data(self):
        """Stopped channels should ignore incoming DA00 updates."""
        self.channel.running = False
        self._send([_var("signal", [99], axes=["x"])])

        assert self.channel.read(0)[0] == 0
        assert self.channel._signal is None
