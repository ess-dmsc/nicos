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
    * Receives matched DA00 messages and pushes to NICOS live plots
    * Ignores pre-reset data until its "start_time" coordinate changes
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from uuid import uuid4

import numpy as np
from streaming_data_types import deserialise_da00
from streaming_data_types.status_x5f2 import deserialise_x5f2
from streaming_data_types.utils import get_schema

from nicos import session
from nicos.core import (
    LIVE,
    POLLER,
    SIMULATION,
    ArrayDesc,
    CommunicationError,
    Override,
    Param,
    floatrange,
    host,
    listof,
    status,
    tupleof,
)
from nicos.devices.generic import CounterChannelMixin, Detector, PassiveChannel
from nicos.utils import byteBuffer, createThread
from nicos_ess.devices.kafka.consumer import KafkaConsumer, KafkaSubscriber
from nicos_ess.devices.kafka.producer import KafkaProducer

COMMAND_TIMEOUT = 5.0


@dataclass
class _JobHealth:
    """What one backend job last said about itself."""

    workflow_id: str
    source_name: str
    code: int
    text: str
    expected_at: float


class DataChannel(CounterChannelMixin, PassiveChannel):
    """Channel for a particular derived device.

    Forwards DA00 'signal' arrays to NICOS live data.
    Supports 1D, 2D, and N-D.

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
        "data_timeout": Param(
            "Maximum wait for initial data, reset confirmation or fresh data",
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
            type=int,
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
        "unit": Override(default="events", settable=False, mandatory=False),
        "fmtstr": Override(default="%d"),
        "pollinterval": Override(default=None, userparam=False, settable=False),
    }

    arraydesc = ArrayDesc("", shape=(), dtype=np.int32)

    def doPreinit(self, mode):
        self._collector = None  # set by LiveDataCollector
        self._signal: np.ndarray | None = None
        self._generation: int | None = None
        self._gate_generation: int | None = None
        self._has_baseline = threading.Event()
        self._last_update = None
        self._started = 0.0
        self.arraydesc = ArrayDesc(self.name, shape=(), dtype=np.int32)
        if session.sessiontype != POLLER:
            self._update_status(status.OK, "")

    def doRead(self, maxage=0):
        return [self.curvalue]

    def doReadArray(self, quality):
        return self._signal

    def arrayInfo(self):
        return self.arraydesc

    def doStatus(self, maxage=0):
        if self.curstatus[0] == status.ERROR:
            return self.curstatus
        backend = (
            self._collector.source_health(self.workflow_id, self.source_name)
            if self._collector
            else (status.OK, "")
        )
        if self.running:
            if backend[0] not in (status.OK, status.WARN):
                self.curstatus = (status.ERROR, backend[1])
            elif (
                time.monotonic()
                - (
                    self._last_update
                    if self._last_update is not None
                    else self._started
                )
                > self.data_timeout
            ):
                self.curstatus = (status.ERROR, "Timed out waiting for fresh data")
            else:
                # WARN is a completed state in NICOS; a warning must not end a count.
                return status.BUSY, backend[1] or self.curstatus[1]
            return self.curstatus
        if backend[0] != status.OK:
            return backend
        return self.curstatus

    def doPrepare(self):
        self.curvalue = 0
        self._signal = None
        self._last_update = None
        self._update_status(status.OK, "")

    def doStop(self):
        self.running = False
        if self.curstatus[0] != status.ERROR:
            self._update_status(status.OK, "")

    def doFinish(self):
        if self.running and self._last_update is None:
            self._update_status(status.ERROR, "No post-reset data received")
        code, text = self.doStatus(0)
        self.doStop()
        if code == status.ERROR:
            raise CommunicationError(self, text)

    def doStart(self):
        self._started = time.monotonic()
        self.running = True
        self._update_status(status.BUSY, "Counting started")

    def _update_status(self, new_status, message):
        self.curstatus = (new_status, message)
        if self._cache:
            self._cache.put(self._name, "status", self.doStatus(), time.time())

    def arm_reset(self):
        """Ignore the current accumulation until a reset starts a new one."""
        if not self._has_baseline.wait(self.data_timeout):
            raise CommunicationError(self, "No initial data received before reset")
        self._gate_generation = self._generation
        self._last_update = None

    @staticmethod
    def _generation_of(by_name) -> int | None:
        """The ``start_time`` marking which accumulation this message belongs to."""
        var = by_name.get("start_time")
        if var is None:
            return None
        data = np.asarray(var.data).reshape(-1)
        return int(data[0]) if data.size else None

    # Called by collector when a matching DA00 arrives
    def update_data_from_da00(self, da00_msg, timestamp_ns: int):
        try:
            variables = list(da00_msg.data)
            by_name = {
                getattr(v, "name", None): v
                for v in variables
                if getattr(v, "name", None)
            }

            generation = self._generation_of(by_name)
            if generation is None:
                if self.running:
                    self._update_status(status.ERROR, "Missing start_time in data")
                return
            if not self.running:
                if "signal" in by_name:
                    self._generation = max(self._generation or generation, generation)
                    self._has_baseline.set()
                return
            if self.curstatus[0] == status.ERROR:
                return
            if self._gate_generation is not None:
                if generation <= self._gate_generation:
                    return
                self._gate_generation = None
            elif self._generation is not None:
                if generation < self._generation:
                    return
                if generation > self._generation:
                    self._generation = generation
                    self._update_status(status.ERROR, "Accumulation reset during count")
                    return
            self._generation = generation

            sig = by_name.get("signal")
            if sig is None:
                return

            arr = np.asarray(sig.data)
            arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
            sig_axes = list(getattr(sig, "axes", [])) or [
                f"dim{i}" for i in range(arr.ndim)
            ]
            estia_labels = ["blade", "wire", "strip"]

            def _coord_for(ax_name: str):
                v = by_name.get(ax_name)
                if v is not None and getattr(v, "axes", None) in (
                    [ax_name],
                    (ax_name,),
                ):
                    return v
                if "/" in ax_name:  # tolerate 'arc/tube' etc.
                    token = ax_name.split("/")[0]
                    v = by_name.get(token)
                    if v is not None and getattr(v, "axes", None) in (
                        [token],
                        (token,),
                    ):
                        return v
                return None

            def _labels_from_coord(var, dim_len):
                if var is None:
                    return np.arange(dim_len, dtype=np.float64), "", False
                vals = np.asarray(var.data)
                unit = getattr(var, "unit", None) or ""
                is_time = False
                if isinstance(unit, str) and unit.startswith("datetime64["):
                    u = unit[len("datetime64[") : -1]
                    scale = {
                        "ns": 1e-9,
                        "us": 1e-6,
                        "ms": 1e-3,
                        "s": 1.0,
                        "m": 60.0,
                        "h": 3600.0,
                    }.get(u, 1.0)
                    vals = vals.astype(np.float64) * scale
                    unit = "s"
                    is_time = True
                else:
                    vals = vals.astype(np.float64, copy=False)

                if vals.shape[-1] == dim_len:
                    return np.ascontiguousarray(vals), unit, is_time
                if vals.shape[-1] == dim_len + 1:
                    mids = 0.5 * (vals[:-1] + vals[1:])
                    return np.ascontiguousarray(mids), unit, is_time
                return np.arange(dim_len, dtype=np.float64), unit, is_time

            if arr.ndim == 0:
                arr = arr.reshape(1)
                sig_axes = ["dim0"]

            if arr.ndim == 1:
                x_idx = 0
                self._signal = np.ascontiguousarray(arr)
                x_labels, x_unit, x_is_time_flag = _labels_from_coord(
                    _coord_for(sig_axes[x_idx]), arr.shape[0]
                )
                labels = [x_labels]
                plot_type = "hist-1d"
                axis_names = [sig_axes[x_idx], "Counts"]
                axis_units = [x_unit, (getattr(sig, "unit", None) or "")]

            # 3D estia layout: collapse last two dims into a 2D view
            elif arr.ndim == 3 and all(label in sig_axes for label in estia_labels):
                y_idx, x_idx = 0, 1
                dimension_lengths = [arr.shape[i] for i in range(arr.ndim)]
                view = arr.reshape(
                    dimension_lengths[0], dimension_lengths[1] * dimension_lengths[2]
                )
                self._signal = np.ascontiguousarray(view)

                x_labels, x_unit, x_is_time_flag = _labels_from_coord(
                    _coord_for(sig_axes[x_idx]), self._signal.shape[1]
                )
                y_labels, y_unit, _ = _labels_from_coord(
                    _coord_for(sig_axes[y_idx]), self._signal.shape[0]
                )
                labels = [x_labels, y_labels]
                plot_type = "hist-3d"
                axis_names = [
                    f"{sig_axes[x_idx]}/{sig_axes[x_idx + 1]}",
                    sig_axes[y_idx],
                ]  # ["blade/wire", "strip"]
                axis_units = [x_unit, y_unit]

            elif arr.ndim == 2 or arr.ndim >= 4:
                # choose two axes and sum over the rest
                def _pick_2d_axes(ax_names):
                    dim_lens = [arr.shape[i] for i in range(arr.ndim)]
                    idx_with_coords = []
                    for i, name in enumerate(ax_names):
                        cv = _coord_for(name)
                        if cv is None:
                            continue
                        clen = np.asarray(cv.data).shape[-1]
                        if clen in (dim_lens[i], dim_lens[i] + 1):
                            idx_with_coords.append(i)
                    if len(idx_with_coords) >= 2:
                        y_idx, x_idx = idx_with_coords[-2], idx_with_coords[-1]
                    else:
                        y_idx, x_idx = max(0, arr.ndim - 2), max(0, arr.ndim - 1)
                    reduce_idxs = [
                        i for i in range(arr.ndim) if i not in (y_idx, x_idx)
                    ]
                    return y_idx, x_idx, reduce_idxs

                y_idx, x_idx, reduce_idxs = _pick_2d_axes(sig_axes)
                view = arr
                for ax in sorted(reduce_idxs, reverse=True):
                    view = view.sum(axis=ax, dtype=view.dtype)
                self._signal = np.ascontiguousarray(view)

                x_labels, x_unit, x_is_time_flag = _labels_from_coord(
                    _coord_for(sig_axes[x_idx]), self._signal.shape[1]
                )
                y_labels, y_unit, _ = _labels_from_coord(
                    _coord_for(sig_axes[y_idx]), self._signal.shape[0]
                )
                labels = [x_labels, y_labels]
                plot_type = "hist-2d"
                axis_names = [sig_axes[x_idx], sig_axes[y_idx]]
                axis_units = [x_unit, y_unit]

            title = (getattr(sig, "label", None) or "").strip() or self.name
            signal_unit = getattr(sig, "unit", None) or ""

            if self._signal is None:
                self.log.warning(
                    f"Data could not be extracted from DA00 for {self.name}"
                )
                return

            self.curvalue = int(self._signal.sum()) if self._signal.size else 0
            self.arraydesc = ArrayDesc(
                self.name, shape=self._signal.shape, dtype=self._signal.dtype
            )
            self._cache.put(self, "value", self.curvalue, time.time())

            self._push_to_nicos(
                plot_type,
                labels,
                timestamp_ns,
                axis_names=axis_names,
                axis_units=axis_units,
                title=title,
                signal_unit=signal_unit,
                x_is_time=x_is_time_flag,
            )
            self._last_update = time.monotonic()
            self._update_status(status.BUSY, "Counting")
        except Exception as exc:
            self._update_status(status.ERROR, str(exc))

    def _push_to_nicos(
        self,
        plot_type: str,
        label_arrays: list[np.ndarray],
        timestamp: int,
        *,
        axis_names: list[str] | None = None,
        axis_units: list[str] | None = None,
        title: str | None = None,
        signal_unit: str | None = None,
        x_is_time: bool = False,
    ):
        if self._signal is None:
            return

        databuffer = [byteBuffer(np.ascontiguousarray(self._signal))]
        datadesc = [
            dict(
                dtype=self._signal.dtype.str,
                shape=self._signal.shape,
                labels={"x": {"define": "classic"}, "y": {"define": "classic"}},
                plotcount=1,
                plot_type=plot_type,
                label_shape=tuple(len(a) for a in label_arrays),
                label_dtypes=tuple(np.dtype(np.float64).str for _ in label_arrays),
                axis_names=axis_names or [],
                axis_units=axis_units or [],
                title=title or "",
                signal_unit=signal_unit or "",
                x_is_time=bool(x_is_time),
            )
        ]

        flat_labels = np.ascontiguousarray(
            np.concatenate(label_arrays), dtype=np.float64
        )
        labelbuffers = [byteBuffer(flat_labels)]

        session.updateLiveData(
            dict(uid=0, time=timestamp, det=self.name, tag=LIVE, datadescs=datadesc),
            databuffer,
            labelbuffers,
        )


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
            default="",
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
        self._jobs: dict[str, _JobHealth] = {}
        self._seen_sources = set()
        self._heartbeat_started = time.monotonic()
        self._stop_status = threading.Event()
        self._published_health: dict[str, tuple[int, str]] = {}

        # Attach collector reference to channels
        for ch in self._data_channels:
            ch._collector = self

        if mode == SIMULATION or session.sessiontype == POLLER:
            return

        # Data subscriber (callbacks)
        self._data_subscriber = KafkaSubscriber(self.brokers)
        self._data_subscriber.subscribe(
            self.data_topics,
            self._on_data_messages,
            self._on_no_data,
        )

        # Status/heartbeat consumer (simple tail thread)
        if self.status_topics:
            self._status_consumer = KafkaConsumer.create(
                self.brokers,
                starting_offset="latest",
                group_id=self._unique_group("status"),
            )
            self._status_consumer.subscribe(self.status_topics)
            self._status_thread = createThread(
                "livedata_status_tail", self._tail_status_topic
            )

        # Commands producer
        if self.commands_topic:
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

        Reset is whole-workflow, so channels sharing a workflow_id are covered
        by one command. Channels are armed first, so that a post-reset message
        arriving before they start is not taken for the old accumulation.
        """
        for ch in self._data_channels:
            ch.arm_reset()
        for workflow_id in self._workflow_ids():
            self.send_workflow_reset_command(workflow_id)
        Detector.doStart(self)

    def source_health(self, workflow_id: str, source_name: str) -> tuple[int, str]:
        """Status of the backend job feeding one contracted source.

        A session that never subscribed has no opinion and reports OK.
        """
        if self._status_consumer is None or not workflow_id:
            return (status.OK, "")
        now = time.monotonic()
        awaiting_heartbeat = (workflow_id, source_name) not in self._seen_sources
        live = [
            job
            for job in self._jobs.values()
            if job.workflow_id == workflow_id
            and job.source_name == source_name
            and job.expected_at + self.status_timeout > now
        ]
        if not live:
            if (
                awaiting_heartbeat
                and now < self._heartbeat_started + self.status_timeout
            ):
                return (status.WARN, "Waiting for job heartbeat")
            return (status.ERROR, f"no running job for {workflow_id}/{source_name}")
        worst = max(live, key=lambda job: job.code)
        return (worst.code, worst.text)

    def _on_data_messages(self, messages: list[tuple[int, bytes]]):
        for timestamp_ns, raw in messages:
            try:
                if get_schema(raw) != "da00":
                    continue
                da = deserialise_da00(raw)

                # Route to matching channels
                self._dispatch_to_channels(timestamp_ns, da)
            except Exception as exc:
                self.log.warning(f"Could not decode/route DA00: {exc}")
        self._publish_health_changes()

    def _on_no_data(self):
        self._publish_health_changes()

    def _tail_status_topic(self):
        while not self._stop_status.is_set():
            # poll() also yields partition-EOF and error events, which carry
            # no payload.
            msg = self._status_consumer.poll(timeout_ms=200)
            if msg is not None and not msg.error():
                try:
                    self._note_job_heartbeat(msg.value())
                except Exception as exc:
                    self.log.warning(f"Could not decode heartbeat: {exc}")
            # Runs on every pass, so a workflow that stops heartbeating expires.
            now = time.monotonic()
            self._jobs = {
                key: job
                for key, job in self._jobs.items()
                if job.expected_at + self.status_timeout > now
            }
            self._publish_health_changes()

    def _publish_health_changes(self):
        """Push health changes and data timeouts into the cache."""
        changed = False
        for ch in self._data_channels:
            health = ch.doStatus(0)
            if health != self._published_health.get(ch.name):
                self._published_health[ch.name] = health
                self._cache.put(ch, "status", health, time.time())
                changed = True
        if changed:
            self._cache.put(self, "status", self.doStatus(0), time.time())

    def _note_job_heartbeat(self, raw: bytes):
        """Record what one x5f2 job heartbeat says.

        ``status_json.status`` is already a NICOS status constant.
        """
        if get_schema(raw) != "x5f2":
            return
        st = deserialise_x5f2(raw)
        payload = json.loads(st.status_json) if st.status_json else {}
        message = payload.get("message") or {}
        if message.get("message_type") != "job":
            return

        job = message["job_id"]
        key = f"{job['source_name']}/{job['job_number']}"
        state = message["state"]
        self._seen_sources.add((message["workflow_id"], job["source_name"]))
        if state == "stopped":
            self._jobs.pop(key, None)
            return
        code = int(payload["status"])
        if code == status.UNKNOWN:
            code = status.ERROR
        self._jobs[key] = _JobHealth(
            workflow_id=message["workflow_id"],
            source_name=job["source_name"],
            code=code,
            text=""
            if code == status.OK
            else (message.get("error") or message.get("warning") or state),
            expected_at=time.monotonic() + max(1, int(st.update_interval // 1000)),
        )

    def _dispatch_to_channels(self, timestamp_ns: int, da):
        if not da.source_name:
            return
        for ch in self._data_channels:
            if ch.device_name == da.source_name:
                ch.update_data_from_da00(da, timestamp_ns)

    def send_workflow_reset_command(self, workflow_id: str):
        """
        Send a workflow-level reset command (for NICOS-derived devices).

        This sends a reset command with only workflow_id (no job_id), which
        resets all jobs of that workflow. Used by device-based channels that
        don't track individual job_numbers.

        Parameters
        ----------
        workflow_id : str
            The workflow ID in format "instrument/name/version"
        """
        if not self._producer or not self.commands_topic:
            raise CommunicationError(self, "No producer or commands_topic configured")

        # Build payload according to ADR 0006
        payload = {
            "kind": "job_command",
            "action": "reset",
            "workflow_id": workflow_id,
            "message_id": str(uuid4()),
        }

        delivery = []

        def _on_delivery(err, msg):
            delivery.append(err)

        try:
            self.log.info(f"Sending workflow reset command for {workflow_id}")
            self._producer.produce(
                self.commands_topic,
                message=json.dumps(payload).encode("utf-8"),
                on_delivery_callback=_on_delivery,
                flush_timeout=COMMAND_TIMEOUT,
            )
        except Exception as exc:
            raise CommunicationError(
                self, f"Error sending workflow reset: {exc}"
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
