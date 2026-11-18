"""Harness tests for the livedata collector and data channels.

The tests make the protocol boundaries explicit:

- the collector owns routing and the workflow reset commands
- channels own array/value updates
- DA00 payloads are injected directly so each test can show exactly which
  input produced the asserted result
"""

import json
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("streaming_data_types")

from streaming_data_types.dataarray_da00 import Variable, serialise_da00
from streaming_data_types.status_x5f2 import serialise_x5f2

from nicos.core import (
    FINAL,
    LIVE,
    SLAVE,
    CommunicationError,
    NicosError,
    status,
)
from nicos_ess.devices.datasources import livedata
from nicos_ess.devices.datasources.livedata_protocol import time_stamp
from nicos_ess.devices.timer import TimerChannel
from test.nicos_ess.test_devices.doubles import (
    StubKafkaConsumer,
    StubKafkaMessage,
    StubKafkaProducer,
    StubKafkaSubscriber,
)
from test.nicos_ess.test_devices.doubles.livedata_messages import wait_for

# On the device topic the DA00 source name is the bare device name.
_SOURCE_NAME = "monitor"

#: A recorded ACK that esslivedata sent for a reset.
_ACK = (Path(__file__).parent / "data" / "livedata" / "ack.json").read_bytes()


def _answer(collector, message_id=None, at=0, error=None):
    """Answer the last reset, or the one with *message_id*, like esslivedata.

    The answer is the recorded ACK, or an ERR if *error* is given. Its Kafka
    timestamp *at* is in ms.
    """
    if message_id is None:
        message_id = json.loads(collector._producer.messages[-1]["message"])[
            "message_id"
        ]
    answer = dict(json.loads(_ACK), message_id=message_id)
    if error:
        answer.update(response="ERR", message=error)
    collector._note_answer(json.dumps(answer).encode(), at)


class ResetProducer(StubKafkaProducer):
    error = None
    deliver = True
    fail = False
    # If this is set, each reset gets an ACK right away, or an ERR with the
    # text in refuse.
    collector = None
    refuse = None

    def produce(self, topic, message, **kwargs):
        if self.fail:
            raise RuntimeError("Producer unavailable")
        callback = kwargs.pop("on_delivery_callback", None)
        super().produce(topic, message, **kwargs)
        if callback and self.deliver:
            callback(self.error, None)
        if self.collector is not None:
            message_id = json.loads(message)["message_id"]
            _answer(self.collector, message_id, error=self.refuse)


@pytest.fixture
def livedata_stubs(monkeypatch):
    """Patch livedata Kafka plumbing with explicit in-memory doubles."""
    producer = ResetProducer()
    # Replace Kafka network I/O with an explicitly driven subscriber.
    monkeypatch.setattr(livedata, "KafkaSubscriber", StubKafkaSubscriber)
    # Replace broker delivery with a controllable in-memory transport.
    monkeypatch.setattr(livedata.KafkaProducer, "create", lambda *a, **k: producer)
    # Avoid a real broker connection. A poll waits a little, as it does with Kafka.
    monkeypatch.setattr(
        livedata.KafkaConsumer,
        "create",
        lambda *a, **k: StubKafkaConsumer(poll_hook=lambda *a, **k: time.sleep(0.01)),
    )
    return producer


def _create_channel(
    daemon_device_harness, name="channel", workflow_id="test/monitor_data/1", **config
):
    """Create one data channel whose device name matches `_SOURCE_NAME`."""
    return daemon_device_harness.create_master(
        livedata.DataChannel,
        name=name,
        workflow_id=workflow_id,
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
        images=channel_names,
        timers=["timer"] if timers else [],
    )
    collector._producer.collector = collector
    if seed:
        _send_data(collector, 500, 111)
    return collector


def _stamps(generation, seconds=1000):
    """Return esslivedata time stamps for *seconds* of data.

    The accumulation starts *generation* ns after 2023-11-14.
    """
    start = 1_700_000_000 * 10**9 + generation
    end = start + int(seconds * 10**9)
    return [_var("start_time", start, unit="ns"), _var("time", end, unit="ns")]


def _send_data(collector, total, generation, seconds=1000, at=0):
    """Send data with the Kafka timestamp *at*, which is in ms."""
    data = [Variable(name="signal", data=np.asarray(total), shape=(), axes=[])]
    if generation is not None:
        data.extend(_stamps(generation, seconds))
    collector._data_subscriber.emit_messages(
        [((1, at), serialise_da00(source_name="monitor", timestamp_ns=0, data=data))]
    )


def _job_heartbeat(
    state,
    nicos_status,
    error=None,
    update_interval=1000,
    source_name="monitor",
    job_number="job-1",
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
                    "job_id": {"source_name": source_name, "job_number": job_number},
                    "workflow_id": "test/monitor_data/1",
                },
            }
        ),
    )


def _make_da00(source_name, variables):
    """Build the minimal DA00-like object the channel update path expects."""
    return SimpleNamespace(source_name=source_name, data=variables)


def _var(name, data, axes=None, unit="", label=None):
    return Variable(name=name, data=np.asarray(data), axes=axes, unit=unit, label=label)


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

    def test_prepare_zeroes_the_value_and_sends_no_empty_frame(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()
        _send_data(collector, 7, 222)
        collector.finish()
        assert channel.readArray(FINAL).tolist() == [7]

        collector.prepare()

        # A LIVE read gives no zeros, which the plot would show as "Σ 0".
        assert channel.readArray(LIVE) is None
        assert channel.read(0) == [0]
        assert channel.readArray(FINAL) is None

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

    def test_da00_routing_updates_the_value_and_the_array(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()

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

        collector._on_data_messages([((1, 0), raw)])

        assert channel.read(0)[0] == 5
        assert channel.readArray(LIVE).tolist() == [2, 3]
        assert channel.arraydesc.dimnames == ["bin_edges"]
        edges = channel.arraydesc.frame.coords["bin_edges"]
        assert edges.values.tolist() == [0.0, 1.0, 2.0]

    @pytest.mark.parametrize(
        "config, unit, counts",
        [
            ({"unit": "ADC", "counts": False}, "ADC", False),
            ({}, "counts", True),
            ({"unit": "", "counts": False}, "", False),
        ],
    )
    def test_a_unitless_signal_takes_the_unit_of_the_channel(
        self, daemon_device_harness, livedata_stubs, config, unit, counts
    ):
        """esslivedata sends monitor counts as dimensionless, so the plot shows
        the unit from the setup. A ratio has unit="" and counts=False there.
        """
        channel = _create_channel(daemon_device_harness, **config)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()
        signal = _var("signal", [0.5], axes=["x"], unit="dimensionless")
        da00 = _make_da00(_SOURCE_NAME, [signal, *_stamps(222)])
        channel.update_data_from_da00(da00, 0)
        channel.readArray(LIVE)

        assert (channel.arraydesc.frame.unit, channel.arraydesc.frame.counts) == (
            unit,
            counts,
        )

    def test_the_detector_returns_the_frame_once_per_message(
        self, daemon_device_harness, livedata_stubs
    ):
        _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()
        _send_data(collector, 7, 222)

        assert collector.readArrays(LIVE)[0].tolist() == [7]
        assert collector.readArrays(LIVE) == [None]
        assert collector.readArrays(FINAL)[0].tolist() == [7]
        collector.stop()

    def test_unreadable_messages_give_one_warning_for_each_kind(
        self, daemon_device_harness, livedata_stubs, caplog
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"], ["status"])
        junk = b"\x00\x00\x00\x00da00" + bytes(range(40))
        collector._data_subscriber.emit_messages([((1, 0), junk)] * 20)
        for _ in range(20):
            collector._status_consumer.queue_record(
                StubKafkaMessage(b"[]", topic="livedata_responses")
            )
        heartbeat = _job_heartbeat("active", status.OK)
        collector._status_consumer.queue_record(
            StubKafkaMessage(heartbeat, topic="status")
        )
        assert wait_for(lambda: channel.status(0) == channel.curstatus)

        assert len([r for r in caplog.records if r.levelname == "WARNING"]) == 2


class TestFreshProcess:
    """A daemon that died mid-count leaves BUSY state in the cache."""

    def test_a_timer_left_counting_starts_idle(self, daemon_device_harness):
        daemon_device_harness.session.cache.put(
            "timer", "curstatus", (status.BUSY, "counting")
        )

        timer = daemon_device_harness.create_master(TimerChannel, name="timer")

        assert timer.status(0) == (status.OK, "idle")

    def test_a_channel_left_counting_starts_idle(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        channel.shutdown()
        # This is what a crash during a count leaves in the cache.
        daemon_device_harness.session.cache.put("channel", "running", True)

        channel = _create_channel(daemon_device_harness)

        assert channel.status(0) == (status.OK, "")
        assert channel.running is False

    def test_a_client_leaves_the_count_of_the_daemon_alone(
        self, daemon_device_harness, livedata_stubs
    ):
        daemon_device_harness.session.cache.put("channel", "running", True)
        channel = _create_channel(daemon_device_harness, mode=SLAVE)
        assert channel.running is True

    def test_the_status_follower_survives_an_error(
        self, daemon_device_harness, livedata_stubs
    ):
        collector = _create_collector(daemon_device_harness, [], ["status"])
        polls = []

        def poll(**kwargs):
            polls.append(1)
            if len(polls) == 1:
                raise RuntimeError("broker gone")

        collector._status_consumer.poll = poll
        deadline = time.monotonic() + 3
        while len(polls) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(polls) >= 2


class TestCountWindow:
    """esslivedata accumulates in steps, and a count keeps the frame that holds
    its time.
    """

    def _counting(self, harness, t):
        channel = _create_channel(harness)
        collector = _create_collector(harness, ["channel"])
        collector.setPreset(t=t)
        collector.prepare()
        collector.start()
        return channel, collector

    def _wait_until_completed(self, collector):
        deadline = time.monotonic() + 5
        while not collector.isCompleted():
            assert time.monotonic() < deadline
            time.sleep(0.01)

    def test_the_first_frame_holding_the_time_preset_is_kept(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._counting(daemon_device_harness, t=2)
        for total, seconds in ((100, 1), (200, 2), (300, 3)):
            _send_data(collector, total, 222, seconds=seconds)
        assert channel.read(0) == [200]
        collector.stop()

    def test_finish_waits_for_late_covering_data(
        self, daemon_device_harness, livedata_stubs, caplog
    ):
        channel, collector = self._counting(daemon_device_harness, t=0.05)
        collector.finish_timeout = 2
        _send_data(collector, 10, 222, seconds=0.02)
        self._wait_until_completed(collector)
        threading.Timer(0.2, _send_data, (collector, 60, 222, 0.06)).start()
        collector.finish()
        assert channel.read(0) == [60]
        assert "sent no data covering" not in caplog.text

    def test_finish_warns_when_no_frame_covers_the_count(
        self, daemon_device_harness, livedata_stubs, caplog
    ):
        channel, collector = self._counting(daemon_device_harness, t=0.05)
        collector.finish_timeout = 0.1
        _send_data(collector, 10, 222, seconds=0.02)
        self._wait_until_completed(collector)
        collector.finish()
        assert channel.read(0) == [10]
        assert "channel sent no data covering the 0.05 s count" in caplog.text

    def test_stop_ends_the_wait_in_finish(self, daemon_device_harness, livedata_stubs):
        _channel, collector = self._counting(daemon_device_harness, t=0.05)
        collector.finish_timeout = 5
        _send_data(collector, 10, 222, seconds=0.02)
        self._wait_until_completed(collector)
        threading.Timer(0.2, collector.stop).start()
        started = time.monotonic()
        collector.finish()
        assert time.monotonic() - started < 2

    def test_a_start_without_prepare_counts_from_zero(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._counting(daemon_device_harness, t=0.05)
        _send_data(collector, 77, 222, seconds=0.1)
        self._wait_until_completed(collector)
        collector.finish()

        collector.start(t=0.05)
        assert channel.read(0) == [0]
        _send_data(collector, 5, 333, seconds=0.1)
        self._wait_until_completed(collector)
        collector.finish()
        assert channel.read(0) == [5]

    def test_a_channel_preset_count_keeps_the_frame_that_reached_it(
        self, daemon_device_harness, livedata_stubs, caplog
    ):
        """The frame holds less data than the wall time of the count, because
        esslivedata publishes once a second."""
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.finish_timeout = 1
        collector.setPreset(channel=100)
        collector.prepare()
        collector.start()
        time.sleep(0.2)
        _send_data(collector, 100, 222, seconds=0.01)
        self._wait_until_completed(collector)
        collector.finish()
        assert channel.read(0) == [100]
        assert "sent no data covering" not in caplog.text

    def test_finish_waits_for_data_still_on_its_way(
        self, daemon_device_harness, livedata_stubs
    ):
        """A count that is shorter than the esslivedata publishing interval
        ends before the first data after its reset arrives.
        """
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()
        collector.finish_timeout = 2
        threading.Timer(0.3, _send_data, (collector, 7, 222, 1)).start()
        started = time.monotonic()
        collector.finish()
        assert time.monotonic() - started < collector.finish_timeout
        assert channel.read(0) == [7]

    @pytest.mark.parametrize(
        "value, unit, seconds",
        [
            (1_700_000_000_500_000_000, "ns", 1_700_000_000.5),
            (1_700_000_000_500_000_000, "datetime64[ns]", 1_700_000_000.5),
            (1_700_000_000_500, "datetime64[ms]", 1_700_000_000.5),
            (1_700_000_000, "s", 1_700_000_000),
            (5, "counts", None),
            # These are in another unit than they say.
            (1_700_000_000_000_000_000, "s", None),
            (1_700_000_000_000_000, "ns", None),
            (1_700_000_000_000, "us", None),
        ],
    )
    def test_time_stamps_in_epoch_seconds(self, value, unit, seconds):
        expected = None if seconds is None else pytest.approx(seconds)
        assert time_stamp(_var("time", value, unit=unit)) == expected

    def test_a_time_with_axes_is_no_time_stamp(self):
        assert time_stamp(_var("time", [1_500_000_000], axes=["x"], unit="ns")) is None

    def test_time_stamps_in_the_wrong_unit_do_not_end_the_count(
        self, daemon_device_harness, livedata_stubs
    ):
        """The time stamps are ns but say s, so the first frame would seem to
        hold far more data than the count needs."""
        channel, collector = self._counting(daemon_device_harness, t=10)
        start = 1_700_000_000 * 10**9
        for total, seconds in ((1, 0.1), (50, 5)):
            data = [
                _var("signal", [total], axes=["x"]),
                _var("start_time", start, unit="s"),
                _var("time", start + int(seconds * 1e9), unit="s"),
            ]
            channel.update_data_from_da00(_make_da00(_SOURCE_NAME, data), 0)
        assert channel.read(0) == [50]
        collector.stop()


def test_another_sources_ack_cannot_satisfy_an_unseeded_channel_preset(
    daemon_device_harness, livedata_stubs
):
    channel = _create_channel(daemon_device_harness)
    daemon_device_harness.create_master(
        livedata.DataChannel,
        name="other",
        workflow_id=channel.workflow_id,
        device_name="monitor_b",
        source_name="monitor_b",
        type="counter",
    )
    collector = _create_collector(
        daemon_device_harness,
        ["channel", "other"],
        status_topics=["heartbeat"],
        seed=False,
    )
    for source in ("monitor", "monitor_b"):
        collector._note_job_heartbeat(
            _job_heartbeat("active", status.OK, source_name=source)
        )
    livedata_stubs.collector = None
    collector.setPreset(channel=100)
    collector.prepare()
    collector.start()
    try:
        commands = [json.loads(item["message"]) for item in livedata_stubs.messages]
        # On the workflow protocol monitor_b answers "all". A targeted command
        # for that job would have its own message ID.
        command = next(
            c
            for c in commands
            if not c.get("job_id") or c["job_id"]["source_name"] == "monitor_b"
        )
        _answer(collector, command["message_id"], at=10)
        _send_data(collector, 9999, 111, at=11)
        assert not collector.isCompleted()
        assert channel.read(0)[0] == 0
    finally:
        collector.stop()


def test_a_silent_preset_channel_fails_while_its_job_still_heartbeats(
    daemon_device_harness, livedata_stubs
):
    channel = _create_channel(daemon_device_harness, data_timeout=0.1)
    collector = _create_collector(daemon_device_harness, ["channel"], ["heartbeat"])
    collector._note_job_heartbeat(_job_heartbeat("active", status.OK))
    collector.setPreset(channel=100)
    collector.prepare()
    collector.start()
    try:
        _send_data(collector, 2, 222)
        assert channel.read(0)[0] == 2
        assert wait_for(lambda: "No data" in channel.status(0)[1], timeout=1)
        with pytest.raises(NicosError, match="No data"):
            collector.isCompleted()
    finally:
        collector.stop()


class TestResetGate:
    """A count must not pick up the accumulation its reset was meant to clear."""

    def _start(self, collector):
        """Start a count whose reset esslivedata answers when the test says so."""
        collector._producer.collector = None
        collector.prepare()
        collector.start()

    def test_signals_without_a_generation_are_skipped(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()

        _send_data(collector, 7, None)

        assert channel.read(0)[0] == 0
        assert channel.status(0)[0] == status.BUSY

    def test_a_reset_just_before_the_count_is_not_its_start(
        self, daemon_device_harness, livedata_stubs
    ):
        """Data after a reset by the user was sent before the answer to the
        reset of the count, even if it arrives later.
        """
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        self._start(collector)
        _answer(collector, at=20)
        _send_data(collector, 50, 222, at=10)
        assert channel.read(0) == [0]
        _send_data(collector, 7, 333, at=20)
        assert channel.read(0) == [7]
        assert channel.status(0)[0] == status.BUSY

    def test_data_before_the_answer_is_ignored(
        self, daemon_device_harness, livedata_stubs
    ):
        """This includes data of the new accumulation, which can overtake the answer."""
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        self._start(collector)
        _send_data(collector, 7, 333, at=20)
        assert channel.read(0) == [0]
        _answer(collector, at=20)
        _send_data(collector, 9, 333, at=1020)
        assert channel.read(0) == [9]
        assert channel.status(0)[0] == status.BUSY

    def test_a_channel_without_earlier_data_waits_for_the_answer(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"], seed=False)
        self._start(collector)
        _send_data(collector, 900000, 111)
        assert channel.read(0) == [0]
        _answer(collector)
        _send_data(collector, 7, 222)
        assert channel.read(0) == [7]

    @pytest.mark.parametrize(
        "error", ["Traceback:\nValueError: no reset for this job", "no reset"]
    )
    def test_a_refused_reset_fails_the_count(
        self, daemon_device_harness, livedata_stubs, error
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        self._start(collector)
        _answer(collector, error=error)
        _send_data(collector, 7, 222)
        assert channel.read(0) == [0]
        assert channel.status(0) == (status.ERROR, error.split("\n")[-1])

    def test_a_reset_refused_before_the_channels_start_fails_the_count(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        livedata_stubs.refuse = "no reset for this job"
        collector.prepare()
        collector.start()
        assert channel.status(0) == (status.ERROR, "no reset for this job")

    def test_the_old_accumulation_of_a_worker_that_answers_later_is_skipped(
        self, daemon_device_harness, livedata_stubs
    ):
        """Each esslivedata worker with a job of the workflow answers the reset.
        The data after the first answer can be the old accumulation of a worker
        that answers later.
        """
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        self._start(collector)
        _answer(collector, at=10)
        _send_data(collector, 9999, 111, at=11)
        assert channel.read(0) == [0]
        _answer(collector, at=12)
        _send_data(collector, 4, 222, at=13)
        assert channel.status(0)[0] == status.BUSY
        collector.finish()
        _answer(collector, at=14)
        assert channel.read(0) == [4]

    def test_a_refusal_after_an_acknowledgement_fails_the_count(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        self._start(collector)
        _answer(collector, at=10)
        _answer(collector, at=11, error="worker 2 has no such job")
        _send_data(collector, 7, 222, at=12)
        assert channel.read(0) == [0]
        assert channel.status(0) == (status.ERROR, "worker 2 has no such job")

    def test_a_lost_answer_fails_a_count_on_the_channel(
        self, daemon_device_harness, livedata_stubs, monkeypatch
    ):
        _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.setPreset(channel=50)
        self._start(collector)
        _send_data(collector, 60, 222, at=10)
        assert not collector.isCompleted()

        now = time.monotonic()
        monkeypatch.setattr(livedata.time, "monotonic", lambda: now + 6)
        with pytest.raises(NicosError, match="did not acknowledge the reset"):
            collector.isCompleted()

    def test_a_channel_without_a_workflow_waits_for_no_answer(
        self, daemon_device_harness, livedata_stubs, monkeypatch
    ):
        channel = _create_channel(daemon_device_harness, workflow_id="")
        collector = _create_collector(daemon_device_harness, ["channel"])
        self._start(collector)
        now = time.monotonic()
        monkeypatch.setattr(livedata.time, "monotonic", lambda: now + 6)
        assert "acknowledge" not in channel.status(0)[1]

    def test_a_lost_answer_is_a_warning_on_a_timed_count(
        self, daemon_device_harness, livedata_stubs, monkeypatch
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.finish_timeout = 0.1
        self._start(collector)
        now = time.monotonic()
        monkeypatch.setattr(livedata.time, "monotonic", lambda: now + 6)
        text = "esslivedata did not acknowledge the reset"
        assert channel.status(0) == (status.BUSY, text)
        collector.finish()
        assert channel.status(0) == (status.WARN, text)

    def test_a_reset_during_the_count_fails_it_until_the_next_count(
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

    def test_the_detector_status_names_only_the_channels_with_a_problem(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        # This channel reads another source, so the data below does not reach it.
        daemon_device_harness.create_master(
            livedata.DataChannel,
            name="channel_b",
            workflow_id="test/monitor_data/1",
            device_name="monitor_b",
            source_name="monitor_b",
            type="counter",
        )
        collector = _create_collector(daemon_device_harness, ["channel_b", "channel"])
        collector.prepare()
        collector.start()
        assert collector.status(0) == (status.BUSY, "counting")

        _send_data(collector, 3, 222)
        _send_data(collector, 9, 333)
        assert channel.status(0) == (status.ERROR, "Accumulation reset during count")
        assert collector.status(0) == (
            status.ERROR,
            "channel=Accumulation reset during count",
        )
        collector.stop()

    def test_reset_clears_a_latched_error(self, daemon_device_harness, livedata_stubs):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()
        _send_data(collector, 3, 333)
        _send_data(collector, 9, 444)
        assert channel.status(0)[0] == status.ERROR
        collector.reset()
        assert channel.status(0)[0] == status.ERROR

        collector.stop()
        collector.reset()
        assert channel.status(0) == (status.OK, "")

    def test_unreadable_data_leaves_nothing_to_blank(
        self, daemon_device_harness, livedata_stubs
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()
        data = [
            Variable(name="signal", data=np.arange(2), shape=(2,), axes=["y", "x"]),
            Variable(name="start_time", data=np.asarray(222), shape=(), axes=[]),
        ]
        collector._data_subscriber.emit_messages(
            [((1, 0), serialise_da00(source_name="monitor", timestamp_ns=0, data=data))]
        )
        assert channel.status(0)[0] == status.BUSY
        assert channel.readArray(FINAL) is None
        _send_data(collector, 7, 222)
        assert channel.read(0) == [7]
        collector.stop()

        collector.prepare()
        assert channel.status(0) == (status.OK, "")

    def test_finish_without_post_reset_data_reads_zero(
        self, daemon_device_harness, livedata_stubs, caplog
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        # Data came before the count, so finish waits only this long for more.
        collector.finish_timeout = 0.1
        collector.prepare()
        collector.start()
        collector.finish()
        assert not channel.running
        assert channel.read(0) == [0]
        assert channel.status(0)[0] == status.OK
        assert "No data received during the count from channel" in caplog.text

    @pytest.mark.parametrize("receive_data", [False, True])
    def test_missing_data_warns_without_ending_the_count(
        self, daemon_device_harness, livedata_stubs, monkeypatch, caplog, receive_data
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
        collector._data_subscriber.emit_idle()
        assert channel.status() == (status.BUSY, "No data received for 10 s")
        assert not collector.isCompleted()
        assert caplog.text.count("No data received for 10 s. The count goes on") == 1
        collector.finish()
        assert channel.status(0) == (status.WARN, "No data received for 10 s")

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

    def test_channel_warns_while_no_job_is_heartbeating(
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
        assert channel.status(0) == (
            status.WARN,
            "No running job for test/monitor_data/1/monitor",
        )

    def test_active_job_lets_the_channel_report_its_own_state(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)

        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))

        assert channel.status(0) == channel.curstatus

    def test_job_waiting_for_data_is_a_warning(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)

        collector._note_job_heartbeat(_job_heartbeat("scheduled", status.DISABLED))

        assert channel.status(0) == (status.WARN, "Job scheduled")

    def test_job_error_is_reported_as_a_warning(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)

        collector._note_job_heartbeat(
            _job_heartbeat("error", status.ERROR, error="workflow blew up")
        )

        assert channel.status(0) == (status.WARN, "workflow blew up")

    def test_a_job_error_that_is_no_text_is_shown_as_text(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(_job_heartbeat("error", status.ERROR, error=5))
        collector._publish_health_changes()
        assert channel.status() == (status.WARN, "5")
        assert collector.status(0) == (status.WARN, "channel=5")

    @pytest.mark.parametrize("interval, alive", [(4000, True), (2000, False)])
    def test_a_job_is_expected_again_after_its_heartbeat_interval(
        self, daemon_device_harness, livedata_stubs, monkeypatch, interval, alive
    ):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(
            _job_heartbeat("active", status.OK, update_interval=interval)
        )
        now = time.monotonic()
        later = now + 3.5 + collector.status_timeout
        monkeypatch.setattr(livedata.time, "monotonic", lambda: later)
        assert (channel.status(0)[0] == status.OK) is alive

    def test_a_heartbeat_interval_in_the_wrong_unit_lets_the_job_expire(
        self, daemon_device_harness, livedata_stubs, monkeypatch
    ):
        """The interval is 2000 s if it is in us but read as ms."""
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(
            _job_heartbeat("active", status.OK, update_interval=2_000_000)
        )
        now = time.monotonic()
        monkeypatch.setattr(livedata.time, "monotonic", lambda: now + 600)
        assert channel.status(0) == (
            status.WARN,
            "No heartbeat from the esslivedata job for monitor",
        )

    def test_a_restarted_job_replaces_its_expired_jobs(
        self, daemon_device_harness, livedata_stubs, monkeypatch
    ):
        channel, collector = self._setup(daemon_device_harness)
        clock = [time.monotonic()]
        monkeypatch.setattr(livedata.time, "monotonic", lambda: clock[0])
        for number in range(5):
            collector._note_job_heartbeat(
                _job_heartbeat("active", status.OK, job_number=f"job-{number}")
            )
            clock[0] += 60
        assert list(collector._jobs) == ["monitor/job-4"]

    def test_stopped_job_is_dropped(self, daemon_device_harness, livedata_stubs):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))

        collector._note_job_heartbeat(_job_heartbeat("stopped", status.OK))

        assert channel.status(0)[0] == status.WARN

    def test_heartbeats_and_the_status_thread_do_not_race(
        self, daemon_device_harness, livedata_stubs
    ):
        # The status thread runs while heartbeats arrive and status is read.
        channel, collector = self._setup(daemon_device_harness)
        interval = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        try:
            for n in range(1000):
                collector._note_job_heartbeat(
                    _job_heartbeat("active", status.OK, source_name=f"monitor{n}")
                )
                assert f"monitor{n}/job-1" in collector._jobs
                channel.status(0)
        finally:
            sys.setswitchinterval(interval)

        assert collector._status_thread.is_alive()

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

        assert channel.status(0) == (
            status.WARN,
            "No heartbeat from the esslivedata job for monitor",
        )

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

        assert channel.status() == (status.WARN, "workflow blew up")

    def test_sibling_job_does_not_hide_stopped_source(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))
        collector._note_job_heartbeat(
            _job_heartbeat("active", status.OK, source_name="another_monitor")
        )
        collector._note_job_heartbeat(_job_heartbeat("stopped", status.OK))
        assert channel.status(0)[0] == status.WARN

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
        assert channel.status(0)[0] == status.WARN

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
        assert channel.status(0) == (status.BUSY, "Job warning")
        _send_data(collector, 100, 222)
        assert collector.isCompleted()
        collector.finish()

    def test_controller_without_a_working_job_fails_the_count(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(
            _job_heartbeat("error", status.ERROR, error="workflow blew up")
        )
        assert channel.status(0)[0] == status.WARN

        collector.setPreset(channel=100)
        collector.prepare()
        assert channel.status(0) == (status.ERROR, "workflow blew up")
        with pytest.raises(NicosError, match="workflow blew up"):
            collector.isCompleted()

        collector.setPreset(t=1)
        assert channel.status(0)[0] == status.WARN

    def test_controller_job_dying_fails_the_running_count(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(_job_heartbeat("active", status.OK))
        collector.start(channel=100)
        _send_data(collector, 7, 222)
        assert not collector.isCompleted()

        collector._note_job_heartbeat(_job_heartbeat("stopped", status.OK))
        with pytest.raises(NicosError, match="No running job"):
            collector.isCompleted()

    def test_controller_waits_for_a_job_that_has_no_data_yet(
        self, daemon_device_harness, livedata_stubs
    ):
        channel, collector = self._setup(daemon_device_harness)
        collector._note_job_heartbeat(_job_heartbeat("scheduled", status.DISABLED))
        collector.start(channel=100)
        assert channel.status(0) == (status.BUSY, "Job scheduled")
        assert not collector.isCompleted()

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
    """DA00 signals of any dimensionality keep their dims, units and coords."""

    @pytest.fixture(autouse=True)
    def setup_channel(self, daemon_device_harness, livedata_stubs):
        self.channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness, ["channel"])
        collector.prepare()
        collector.start()

    def _send(self, variables):
        """Inject one DA00 payload directly into the channel update path."""
        variables = [*variables, _var("start_time", 111)]
        da00 = _make_da00(_SOURCE_NAME, variables)
        self.channel.update_data_from_da00(da00, 0)

    def _array(self):
        return self.channel.readArray(FINAL)

    def test_scalar_signal(self):
        """Scalar signals are normalised into a one-element 1-D array."""
        self._send([_var("signal", 42, axes=["dim0"])])

        assert self.channel.read(0)[0] == 42
        assert self._array().shape == (1,)

    def test_1d_signal_with_its_coords_errors_and_name(self):
        self._send(
            [
                _var(
                    "signal", [1.0, np.nan, 3.0], axes=["x"], unit="counts", label="I"
                ),
                _var("errors", [1.0, 2.0, 3.0], axes=["x"]),
                _var("x", [0.0, 1.0, 2.0, 3.0], axes=["x"], unit="mm"),
                # This variable fits no dim of the signal and is left out.
                _var("frame_total", [5, 6], axes=["frame"]),
            ]
        )

        # The NaN bin is not counted.
        assert self.channel.read(0)[0] == 4
        assert np.isnan(self._array()[1])
        desc = self.channel.arraydesc
        assert (desc.frame.unit, desc.frame.title) == ("counts", "I")
        assert desc.frame.errors.tolist() == [1.0, 2.0, 3.0]
        assert list(desc.frame.coords) == ["x"]
        assert desc.frame.coords["x"].unit == "mm"

    @pytest.mark.parametrize(
        "signal, value",
        [
            ([0.3, 0.45], 0.75),
            ([np.inf, 5.0, -np.inf, 6.0], 11.0),
            (np.array([2**62, 2**62], dtype=np.int64), 2.0**63),
        ],
    )
    def test_the_value_is_the_sum_of_the_finite_values(self, signal, value):
        self._send([_var("signal", signal, axes=["x"])])

        assert self.channel.read(0)[0] == pytest.approx(value)
        assert self._array().tolist() == np.asarray(signal).tolist()

    def test_2d_signal(self):
        data = np.arange(6, dtype=np.float64).reshape(2, 3)
        self._send(
            [
                _var("signal", data, axes=["y", "x"]),
                _var("x", [0.0, 1.0, 2.0, 3.0], axes=["x"]),
                _var("y", [0.0, 1.0, 2.0], axes=["y"]),
            ]
        )

        assert self.channel.read(0)[0] == 15
        assert self._array().shape == (2, 3)
        assert self.channel.arraydesc.dimnames == ["y", "x"]

    @pytest.mark.parametrize(
        "shape, axes",
        [((2, 3, 4), ["blade", "wire", "strip"]), ((2, 3, 4, 5), ["a", "b", "c", "d"])],
    )
    def test_nd_signals_are_kept_whole(self, shape, axes):
        """The client decides which dims to show, so the channel keeps all."""
        data = np.ones(shape, dtype=np.int32)
        self._send([_var("signal", data, axes=axes)])

        assert self.channel.read(0) == [data.size]
        assert self._array().shape == shape
        assert self.channel.arraydesc.dimnames == axes

    @pytest.mark.parametrize(
        "variables, why",
        [
            ([_var("not_signal", [1, 2, 3], axes=["x"])], "no signal"),
            ([_var("signal", np.ones((2, 2)), axes=["y", "y"])], "repeated dims"),
            (
                [
                    _var("signal", [1, 2], axes=["t"]),
                    _var("t", [0, 1], axes=["t"], unit="datetime64"),
                ],
                "unknown time unit",
            ),
        ],
    )
    def test_unreadable_payloads_are_ignored(self, caplog, variables, why):
        """Unreadable payloads leave the channel unchanged.

        Only the first one gives a warning, because esslivedata may have changed
        its format.
        """
        for _ in range(2):
            self._send(variables)

        assert self.channel.read(0)[0] == 0
        assert self._array() is None
        warned = [r for r in caplog.records if r.levelname == "WARNING"]
        assert [why in r.getMessage() for r in warned] == [True]

    def test_consecutive_updates_replace_value(self):
        """Later DA00 updates should replace, not accumulate, the cached signal."""
        self._send([_var("signal", [1, 2], axes=["x"])])
        assert self.channel.read(0)[0] == 3

        self._send([_var("signal", [10, 20], axes=["x"])])
        assert self.channel.read(0)[0] == 30
        assert self._array().tolist() == [10, 20]

    def test_channel_not_running_ignores_data(self):
        """Stopped channels should ignore incoming DA00 updates."""
        self.channel.running = False
        self._send([_var("signal", [99], axes=["x"])])

        assert self.channel.read(0)[0] == 0
        assert self._array() is None
