"""
NICOS data source devices for consuming ESSLivedata and sending light commands.

- LiveDataCollector:
    * Subscribes to DA00 data topics (including LIVEDATA_NICOS_DATA)
    * Tails X5F2 status/heartbeat topics
    * Routes DA00 to DataChannel(s) by device_name
    * Sends workflow-level reset commands when counting starts

- DataChannel:
    * Uses a "device_name" (from ESSlivedata device contract) for device-based
      channels (LIVEDATA_NICOS_DATA topic)
    * Keeps the latest matched DA00 message as a `live_frame.Frame`, read
      as the channel's array, so it reaches clients like any other image
    * Ignores data until esslivedata has acknowledged the reset of the count
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, replace
from uuid import uuid4

import numpy as np
from streaming_data_types import deserialise_da00
from streaming_data_types.utils import get_schema

from nicos import session
from nicos.core import (
    LIVE,
    MASTER,
    POLLER,
    SIMULATION,
    CommunicationError,
    Override,
    Param,
    floatrange,
    host,
    listof,
    status,
    tupleof,
)
from nicos.devices.generic import (
    CounterChannelMixin,
    Detector,
    ImageChannelMixin,
    PassiveChannel,
)
from nicos.utils import createThread
from nicos_ess.devices.datasources import livedata_protocol as proto
from nicos_ess.devices.datasources.livedata_protocol import (
    frame_from_da00,
    job_health,
    parse_heartbeat,
)
from nicos_ess.devices.kafka.consumer import KafkaConsumer, KafkaSubscriber
from nicos_ess.devices.kafka.producer import KafkaProducer
from nicos_ess.utilities.limited_warnings import LimitedWarnings
from nicos_ess.utilities.live_frame import Frame, LiveArrayDesc

COMMAND_TIMEOUT = 5.0


def data_seconds(frame):
    """Return how many seconds of data a frame holds according to its time stamps."""
    meta = frame.meta if frame else {}
    if "start_time" in meta and "time" in meta:
        return meta["time"] - meta["start_time"]
    return 0.0


@dataclass
class _JobHealth:
    """What one backend job last said about itself."""

    workflow_id: str
    source_name: str
    job_number: str
    code: int
    text: str
    expected_at: float


class DataChannel(ImageChannelMixin, CounterChannelMixin, PassiveChannel):
    """Channel for a particular derived device.

    The array is the ``signal`` of the latest DA00 message in the count and
    can have any number of dimensions. A `LiveArrayDesc` describes it. The
    value is the sum of the finite values of the signal. Attach the channel to
    the detector as one of its ``images``.

    Uses a device_name to match messages from the
    LIVEDATA_NICOS_DATA topic (without job_number)
    """

    parameters = {
        "device_name": Param(
            "Device name (from ESSlivedata device contract, for NICOS_DATA topic)",
            type=str,
            userparam=True,
            settable=True,
            default="",
        ),
        "workflow_id": Param(
            "Workflow ID (instrument/name/version) for device-based channels",
            type=str,
            userparam=False,
            settable=True,
            default="",
        ),
        "source_name": Param(
            "Source owning this device, from the ESSlivedata device contract",
            type=str,
            mandatory=True,
        ),
        "counts": Param(
            "Whether the values are counts that the live views sum when they "
            "combine bins. The ADC values of a beam monitor are not counts.",
            type=bool,
            default=True,
            userparam=False,
        ),
        "data_timeout": Param(
            "Time without data after which the channel warns",
            type=floatrange(0.1),
            default=10.0,
            unit="s",
        ),
        "curstatus": Param(
            "Store the current device status",
            internal=True,
            type=tupleof(int, str),
            settable=True,
        ),
        "curvalue": Param(
            "Store the current device value (sum of signal)",
            internal=True,
            type=float,
            settable=True,
        ),
        "running": Param(
            "Indicates if the channel is actively counting",
            internal=True,
            type=bool,
            default=False,
            settable=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(default="counts", settable=False, mandatory=False),
        "fmtstr": Override(default="%d"),
        "pollinterval": Override(default=None, userparam=False, settable=False),
    }

    def doPreinit(self, mode):
        self._collector = None  # set by LiveDataCollector
        # The Kafka thread writes these and the count loop reads them.
        self._frame_lock = threading.Lock()
        self._frame: Frame | None = None
        # The count needs this many seconds of data.
        self._need: float | None = None
        # This is set once a frame holds enough data.
        self._covered = threading.Event()
        self._live_sent: Frame | None = None
        self.arraydesc = LiveArrayDesc(self.name, (0,), np.float64, ["dim_0"])
        # The start_time of the accumulation that this count reads.
        self._generation: int | None = None
        # The Kafka timestamp in ms of the ACK to the reset of this count.
        self._acked_at = np.inf
        # The collector sets this to the time when it sent the reset of the
        # workflow of this channel.
        self._reset_at = np.inf
        # _seen_generation holds the start_time of the latest message. doPrepare
        # copies it to _stale_generation, so that the count can skip the
        # accumulation from before its reset.
        self._seen_generation = self._stale_generation = None
        self._warnings = LimitedWarnings(self.log)
        self._outage_logged = False
        self._last_data = time.monotonic()
        # Data from before the reset also updates this.
        self._heard = -np.inf

    def doInit(self, mode):
        if mode == MASTER:
            # A daemon that died during a count can leave `running` set in the
            # cache. That would keep the channel BUSY and the next count would
            # wait for it forever.
            self.running = False
            self._update_status(status.OK, "")

    def doRead(self, maxage=0):
        return [self.curvalue]

    def doStatus(self, maxage=0):
        """Missing data is a warning, and a count keeps waiting for it.

        The exception is a channel whose preset controls the count: without a
        working job behind it the preset can never be reached, so that is an
        error.
        """
        if self.curstatus[0] == status.ERROR:
            return self.curstatus
        code, text = self._data_health()
        if code == status.ERROR and self.iscontroller:
            return code, text
        if self.running:
            # WARN is a completed state in NICOS; a warning must not end a count.
            return status.BUSY, text or self.curstatus[1]
        if code != status.OK:
            return status.WARN, text
        return self.curstatus

    def _data_health(self) -> tuple[int, str]:
        """Status of the data supply: the backend job, then the data itself."""
        if self._collector is None or not self._collector.subscribed:
            return status.OK, ""
        health = self._collector.source_health(self.workflow_id, self.source_name)
        if health[0] != status.OK:
            return health
        late = time.monotonic() > self._reset_at + COMMAND_TIMEOUT
        if late and self._acked_at == np.inf:
            return status.ERROR, "esslivedata did not acknowledge the reset"
        if time.monotonic() - self._last_data > self.data_timeout:
            # A preset that gets no data can never be reached.
            code = status.ERROR if self.iscontroller else status.WARN
            return code, f"No data received for {self.data_timeout:g} s"
        return status.OK, ""

    def doPrepare(self):
        """Zero the value, drop the frame and ignore all data until esslivedata
        acknowledges the next reset.

        The plots keep showing the data of the previous count until new data
        arrives. The collector also calls this when a count starts.
        """
        self.curvalue = 0
        with self._frame_lock:
            self._frame = self._generation = None
            self._acked_at = self._reset_at = np.inf
            self._stale_generation = self._seen_generation
            self._outage_logged = False
            self._need = None
            self._covered.clear()
        self._warnings.clear()
        self._update_status(status.OK, "")

    def need_data_for(self, seconds):
        """Keep the first frame of this count that holds *seconds* of data.

        esslivedata publishes its accumulation about once a second, so the
        latest frame at the end of the count can miss up to a second of data.
        The time stamps of a frame tell how much data it holds.
        """
        with self._frame_lock:
            self._need = seconds
            if self._frame is not None and data_seconds(self._frame) >= seconds - 1e-3:
                self._covered.set()

    def doReadArray(self, quality):
        """Return the latest frame. A LIVE read returns each frame only once."""
        frame = self._frame
        if frame is None or (quality == LIVE and frame is self._live_sent):
            return None
        self._live_sent = frame
        self.arraydesc = LiveArrayDesc.of(frame, self.name)
        return frame.data

    def doStop(self):
        self.running = False
        # This ends the wait in finish().
        self._covered.set()
        if self.curstatus[0] != status.ERROR:
            self._update_status(status.OK, "")

    def doReset(self):
        if not self.running:
            self._update_status(status.OK, "")

    def doFinish(self):
        code, text = self.curstatus
        self.doStop()
        if code == status.ERROR:
            raise CommunicationError(self, text)

    def doStart(self):
        self._last_data = time.monotonic()
        self.running = True
        # The status is already ERROR if esslivedata refused the reset.
        if self.curstatus[0] != status.ERROR:
            self._update_status(status.BUSY, "Counting started")

    def _update_status(self, new_status, message):
        self.curstatus = (new_status, message)
        if self._cache:
            self._cache.put(self._name, "status", self.doStatus(), time.time())

    @staticmethod
    def _generation_of(by_name) -> int | None:
        """The ``start_time`` marking which accumulation this message belongs to."""
        var = by_name.get("start_time")
        if var is None:
            return None
        data = np.asarray(var.data).reshape(-1)
        return int(data[0]) if data.size else None

    # The collector calls this for each matching DA00 message. The Kafka
    # timestamp *sent* is in ms.
    def update_data_from_da00(self, da00_msg, sent):
        try:
            by_name = {v.name: v for v in da00_msg.data if v.name}

            generation = self._generation_of(by_name)
            if generation is None:
                if self.running:
                    self._ignore("it has no start_time")
                return
            self._seen_generation = generation
            if "signal" in by_name:
                self._heard = time.monotonic()
            if not self.running:
                if "signal" in by_name:
                    self._last_data = time.monotonic()
                return
            # Skip data after a failure and data sent before the reset. A worker
            # that answers the reset after another one can still send the
            # accumulation from before the reset.
            if (
                self.curstatus[0] == status.ERROR
                or sent < self._acked_at
                or generation == self._stale_generation
            ):
                return

            frame = frame_from_da00(by_name, self.name)
            if frame.unit in ("", "dimensionless"):
                # esslivedata sends monitor counts without a unit, for example.
                # A ratio needs unit="" and counts=False in the setup.
                frame = replace(frame, unit=self.unit)
            frame = replace(frame, counts=self.counts)
            finite = np.isfinite(frame.data)
            total = float(np.sum(frame.data, where=finite, dtype=np.float64))
            with self._frame_lock:
                if self._covered.is_set():
                    return
                if self._generation is None:
                    self._generation = generation
                elif generation != self._generation:
                    self._update_status(status.ERROR, "Accumulation reset during count")
                    return
                self._frame = frame
                self.curvalue = total
                # Set the event last because finish() reads the value as soon
                # as the event is set.
                if self._need is not None and data_seconds(frame) >= self._need - 1e-3:
                    self._covered.set()
            self._last_data = time.monotonic()
        except Exception as exc:
            self._ignore(exc)

    def _ignore(self, why):
        self._warnings.warn("data", "ignoring a message from esslivedata: %s", why)


class LiveDataCollector(Detector):
    """
    One device to:
      * consume DA00 data (KafkaSubscriber with callbacks)
      * tail X5F2 status/heartbeat topics (KafkaConsumer in a small thread)
      * route each message to the DataChannel whose device_name matches
      * reset the workflows behind its channels when a count starts
    """

    parameters = {
        "brokers": Param(
            "List of kafka brokers to connect to",
            type=listof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "data_topics": Param(
            "Kafka topic(s) where DA00 messages are written",
            type=listof(str),
            preinit=True,
            mandatory=True,
            userparam=False,
        ),
        "status_topics": Param(
            "Kafka topic(s) where X5F2 status/heartbeat is written",
            type=listof(str),
            default=[],
            preinit=True,
            userparam=False,
        ),
        "commands_topic": Param(
            "Kafka topic to which we send job_command/workflow_config",
            type=str,
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "cfg_group_id": Param(
            "Kafka consumer group base for status/responses",
            type=str,
            default="nicos-livedata",
            settable=True,
            userparam=False,
        ),
        "finish_timeout": Param(
            "How long finish() waits for data covering the whole count",
            type=floatrange(0),
            default=10,
            unit="s",
            userparam=False,
            settable=True,
        ),
        "status_timeout": Param(
            "Consider disconnected if no heartbeat within N seconds beyond interval",
            type=int,
            default=5,
            settable=True,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "liveinterval": Override(type=floatrange(0.5), default=1),
        "pollinterval": Override(default=None, userparam=False, settable=False),
    }

    # internals
    _data_subscriber: KafkaSubscriber | None = None
    _status_consumer: KafkaConsumer | None = None
    _producer: KafkaProducer | None = None

    def doPreinit(self, mode):
        Detector.doPreinit(self, mode)
        self._data_channels = [
            ch for ch in self._channels if isinstance(ch, DataChannel)
        ]
        self._data_subscriber = None
        self._status_consumer = None
        self._status_thread = None
        self._producer = None
        # Maps the message_id of each reset in this count to its workflow and,
        # for the reset of one job, to the source of that job.
        self._resets = {}
        # Written by the status thread, read by channel status calls
        self._jobs_lock = threading.Lock()
        self._jobs: dict[str, _JobHealth] = {}
        self._seen_sources = set()
        self._started = time.monotonic()
        self._heartbeat_started = time.monotonic()
        self._stop_status = threading.Event()
        self._published_health: dict[str, tuple[int, str]] = {}
        self._warnings = LimitedWarnings(self.log)

        # Attach collector reference to channels
        for ch in self._data_channels:
            ch._collector = self

    def doInit(self, mode):
        Detector.doInit(self, mode)
        # Subscribe only after Detector.doInit, because a message that arrives
        # earlier would find the status and presets missing.
        if mode == SIMULATION or session.sessiontype == POLLER:
            return

        # Data subscriber (callbacks)
        self._data_subscriber = KafkaSubscriber(self.brokers)
        self._data_subscriber.subscribe(
            self.data_topics,
            self._on_data_messages,
            self._on_no_data,
        )

        # A simple thread follows the heartbeats and the answers to commands.
        self._responses_topic = proto.responses_topic(self.commands_topic)
        self._status_consumer = KafkaConsumer.create(
            self.brokers,
            starting_offset="latest",
            group_id=self._unique_group("status"),
        )
        self._status_consumer.subscribe([*self.status_topics, self._responses_topic])
        self._status_thread = createThread(
            "livedata_status_tail", self._tail_status_topic
        )

        self._producer = KafkaProducer.create(
            self.brokers, **{"message.timeout.ms": int(COMMAND_TIMEOUT * 1000)}
        )

    def _unique_group(self, label: str) -> str:
        base = self.cfg_group_id or "nicos-livedata"
        return f"{base}-{label}-{uuid4().hex}"

    def _workflow_ids(self) -> list[str]:
        """The distinct workflows backing this detector's channels."""
        return list(
            dict.fromkeys(
                ch.workflow_id
                for ch in self._data_channels
                if ch.device_name and ch.workflow_id
            )
        )

    def doStart(self):
        """Reset the accumulation behind every channel, then start counting.

        Channels take data only after esslivedata has acknowledged the reset.
        Every job of a workflow answers a workflow reset with the same message
        ID, so its ACK cannot tell which job has reset. If the heartbeats name
        the job of every source of a workflow, each job gets its own reset and
        its ACK opens only the channels of its source. Otherwise the whole
        workflow gets one reset, because a job that NICOS does not know cannot
        be reset on its own.
        """
        # A late answer to the reset of an earlier count must not count.
        self._resets = {}
        for ch in self._data_channels:
            ch.prepare()
        for workflow_id in self._workflow_ids():
            for job in self._jobs_of(workflow_id) or [None]:
                self.send_workflow_reset_command(workflow_id, job)
        self._started = time.monotonic()
        Detector.doStart(self)
        _, _, seconds = self._timer_preset()
        if seconds:
            for ch in self._data_channels:
                ch.need_data_for(seconds)

    def _jobs_of(self, workflow_id):
        """Return the live jobs of *workflow_id* if they cover all its sources."""
        sources = {
            ch.source_name
            for ch in self._data_channels
            if ch.device_name and ch.workflow_id == workflow_id
        }
        now = time.monotonic()
        with self._jobs_lock:
            jobs = [
                job
                for job in self._jobs.values()
                if job.workflow_id == workflow_id
                and job.expected_at + self.status_timeout > now
            ]
        return jobs if sources <= {job.source_name for job in jobs} else []

    def doFinish(self):
        self._wait_for_data(self._count_seconds())
        silent = [ch.name for ch in self._data_channels if ch._frame is None]
        Detector.doFinish(self)
        if silent:
            self.log.warning(
                "No data received during the count from %s", ", ".join(silent)
            )

    def doStatus(self, maxage=0):
        """Return the status with a text that names only the channels with a problem.

        That way an abort message starts with the cause of the abort.
        """
        code, _ = Detector.doStatus(self, maxage)
        problems = []
        for ch in self._channels:
            st, text = ch.status(maxage)
            if st not in (status.OK, status.BUSY) or (
                ch in self._data_channels and ch._data_health()[0] != status.OK
            ):
                problems.append(f"{ch}={text}")
        return code, ", ".join(problems) or ("counting" if code == status.BUSY else "")

    def _timer_preset(self):
        for timer in self._attached_timers:
            for name, value in self._channel_presets.get(timer, ()):
                if float(value) > 0:
                    return timer, name, float(value)
        return None, None, None

    def _count_seconds(self):
        timer, name, seconds = self._timer_preset()
        if seconds and timer.presetReached(name, seconds, 0):
            return seconds
        for ch in self._controlchannels:
            presets = self._channel_presets.get(ch, ())
            if isinstance(ch, DataChannel) and any(
                ch.presetReached(n, v, 0) for n, v in presets
            ):
                return data_seconds(ch._frame)
        return time.monotonic() - self._started

    def _wait_for_data(self, seconds):
        """Wait until every channel with data holds *seconds* of it.

        This includes channels whose data is still on the way. esslivedata
        publishes about once a second, so a short count can end before the
        first data after its reset arrives.
        """
        now = time.monotonic()
        channels = [
            ch
            for ch in self._data_channels
            if ch.running
            and (ch._frame is not None or now - ch._heard < ch.data_timeout)
        ]
        for ch in channels:
            ch.need_data_for(seconds)
        deadline = now + self.finish_timeout
        short = [
            ch.name
            for ch in channels
            if not ch._covered.wait(max(0, deadline - time.monotonic()))
        ]
        if short:
            self.log.warning(
                "%s sent no data covering the %.3g s count within %g s, so "
                "their values miss the end of the count",
                ", ".join(short),
                seconds,
                self.finish_timeout,
            )

    @property
    def subscribed(self) -> bool:
        """Whether this session consumes livedata at all."""
        return self._data_subscriber is not None

    def source_health(self, workflow_id: str, source_name: str) -> tuple[int, str]:
        """Status of the backend job feeding one contracted source.

        A session that never subscribed has no opinion and reports OK.
        """
        if not self.status_topics or not workflow_id:
            return (status.OK, "")
        now = time.monotonic()
        with self._jobs_lock:
            awaiting_heartbeat = (workflow_id, source_name) not in self._seen_sources
            jobs = [
                job
                for job in self._jobs.values()
                if job.workflow_id == workflow_id and job.source_name == source_name
            ]
        live = [job for job in jobs if job.expected_at + self.status_timeout > now]
        if not live:
            if jobs:
                # The job did not stop, so the service or Kafka is down.
                return (
                    status.ERROR,
                    f"No heartbeat from the esslivedata job for {source_name}",
                )
            if (
                awaiting_heartbeat
                and now < self._heartbeat_started + self.status_timeout
            ):
                return (status.WARN, "Waiting for job heartbeat")
            return (status.ERROR, f"No running job for {workflow_id}/{source_name}")
        worst = max(live, key=lambda job: job.code)
        return (worst.code, worst.text)

    def _on_data_messages(self, messages):
        for (_type, sent), raw in messages:
            try:
                if get_schema(raw) != "da00":
                    continue
                da = deserialise_da00(raw)

                # Route to matching channels
                self._dispatch_to_channels(da, sent)
            except Exception as exc:
                self._warnings.warn("data", "could not read a da00 message: %s", exc)
        self._publish_health_changes()

    def _on_no_data(self):
        self._publish_health_changes()

    def _tail_status_topic(self):
        while not self._stop_status.is_set():
            try:
                # poll() also yields partition-EOF and error events, which
                # carry no payload.
                msg = self._status_consumer.poll(timeout_ms=200)
                if msg is not None and not msg.error():
                    try:
                        if msg.topic() == self._responses_topic:
                            self._note_answer(msg.value(), msg.timestamp()[1])
                        else:
                            self._note_job_heartbeat(msg.value())
                    except Exception as exc:
                        self._warnings.warn(
                            msg.topic(),
                            "could not read a message on %s: %s",
                            msg.topic(),
                            exc,
                        )
                # Check on every pass so that a job which stops heartbeating
                # is noticed.
                self._publish_health_changes()
            except Exception as exc:
                # The thread must keep running, otherwise a dead job looks
                # alive.
                self._warnings.warn(
                    "poll", "following the status topic failed: %s", exc
                )
                self._stop_status.wait(1)

    def _publish_health_changes(self):
        """Push health changes and data timeouts into the cache.

        The first outage in a count is logged. It is no error, but the data
        has a gap.
        """
        changed = False
        for ch in self._data_channels:
            code, text = ch._data_health()
            if code != status.OK and ch.running and not ch._outage_logged:
                ch._outage_logged = True
                ch.log.warning(
                    "%s. The count goes on, but the value may miss data", text
                )
            health = ch.doStatus(0)
            if health != self._published_health.get(ch.name):
                self._published_health[ch.name] = health
                self._cache.put(ch, "status", health, time.time())
                changed = True
        if changed:
            self._cache.put(self, "status", self.doStatus(0), time.time())

    def _note_answer(self, raw, sent):
        """Handle the esslivedata answer to a command.

        The Kafka timestamp *sent* of the answer is in ms. An ACK of a reset
        lets the channels that it reset take the data sent after it. An ERR
        puts these channels in ERROR.
        """
        answer = proto.parse_ack(raw)
        workflow_id, source = self._resets.get(answer["message_id"], (None, None))
        for ch in self._data_channels:
            if (
                workflow_id
                and ch.workflow_id == workflow_id
                and source in (None, ch.source_name)
            ):
                if answer["ok"]:
                    ch._acked_at = sent
                else:
                    ch._update_status(status.ERROR, proto.headline(answer["message"]))

    def _note_job_heartbeat(self, raw: bytes):
        parsed = parse_heartbeat(raw)
        if parsed is None or parsed[0] != "job":
            return
        job = parsed[1]
        key = f"{job['source_name']}/{job['job_number']}"
        source = job["workflow_id"], job["source_name"]
        now = time.monotonic()
        with self._jobs_lock:
            self._seen_sources.add(source)
            # A restarted job has a new number, so the expired jobs of its
            # source go.
            self._jobs = {
                k: j
                for k, j in self._jobs.items()
                if (j.workflow_id, j.source_name) != source
                or j.expected_at + self.status_timeout > now
            }
            if job["state"] == "stopped":
                self._jobs.pop(key, None)
                return
            code, text = job_health(job)
            self._jobs[key] = _JobHealth(
                workflow_id=job["workflow_id"],
                source_name=job["source_name"],
                job_number=job["job_number"],
                code=code,
                text=text,
                expected_at=now + job["interval"],
            )

    def _dispatch_to_channels(self, da, sent):
        if not da.source_name:
            return
        for ch in self._data_channels:
            if ch.device_name == da.source_name:
                ch.update_data_from_da00(da, sent)

    def send_workflow_reset_command(self, workflow_id: str, job=None):
        """Reset all jobs of *workflow_id*, or only *job* if it is given.

        The workflow ID has the format "instrument/name/version".
        """
        if not self._producer or not self.commands_topic:
            raise CommunicationError(self, "No producer or commands_topic configured")

        # Build payload according to ADR 0006
        payload = {"kind": "job_command", "action": "reset", "message_id": str(uuid4())}
        if job:
            payload["job_id"] = {
                "source_name": job.source_name,
                "job_number": job.job_number,
            }
        else:
            payload["workflow_id"] = workflow_id
        source = job.source_name if job else None

        delivery = []

        def _on_delivery(err, msg):
            delivery.append(err)

        # Register the reset before sending it, because the answer can come
        # right away.
        self._resets[payload["message_id"]] = workflow_id, source
        for ch in self._data_channels:
            if ch.workflow_id == workflow_id and source in (None, ch.source_name):
                ch._reset_at = time.monotonic()
        try:
            self.log.debug("sending a reset command for %s %s", workflow_id, source)
            self._producer.produce(
                self.commands_topic,
                message=json.dumps(payload).encode("utf-8"),
                on_delivery_callback=_on_delivery,
                flush_timeout=COMMAND_TIMEOUT,
            )
        except Exception as exc:
            raise CommunicationError(
                self, f"Could not send workflow reset: {exc}"
            ) from exc
        if not delivery:
            raise CommunicationError(self, "Workflow reset command delivery timed out")
        if delivery[0] is not None:
            raise CommunicationError(
                self, f"Workflow reset delivery failed: {delivery[0]}"
            )

    def doShutdown(self):
        self._stop_status.set()
        try:
            if self._data_subscriber:
                self._data_subscriber.close()
        finally:
            if self._status_thread:
                self._status_thread.join()
            if self._status_consumer:
                self._status_consumer.close()
