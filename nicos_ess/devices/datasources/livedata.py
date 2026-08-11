"""
NICOS data source devices for consuming ESSLivedata and sending light commands.

- LiveDataCollector:
    * Subscribes to DA00 data topics (including LIVEDATA_NICOS_DATA)
    * Tails X5F2 status/heartbeat topics
    * (optional) Tails responses topics
    * Maintains a JobRegistry and publishes it into NICOS cache
    * Routes DA00 to DataChannel(s) by DeviceSelector
    * Provides job_command helpers (reset/stop/remove)

- DataChannel:
    * User selects either:
      - A "selector" string of the form:
        "<instr>/<ns>/<name>/<version>@<source>#<job_number>/<output>"
        for job-based channels (regular data topics)
      - Or a "device_name" (from ESSlivedata device contract) for device-based
        channels (LIVEDATA_NICOS_DATA topic)
    * Receives matched DA00 messages and pushes to NICOS live plots
    * Offers convenience methods reset()/stop()/remove() that send JobCommand
    * For device-based channels, reset() sends workflow-level commands
"""

from __future__ import annotations

import json
import threading
import time
from typing import List, Optional, Tuple
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
    Moveable,
    Override,
    Param,
    floatrange,
    host,
    listof,
    status,
    tupleof,
)
from nicos.devices.generic import CounterChannelMixin, Detector, PassiveChannel
from nicos.utils import byteBuffer, createThread, num_sort, sleep
from nicos_ess.devices.datasources.livedata_utils import (
    DeviceSelector,
    JobInfo,
    JobRegistry,
    WorkflowId,
    parse_result_key,
)
from nicos_ess.devices.kafka.consumer import KafkaConsumer, KafkaSubscriber
from nicos_ess.devices.kafka.producer import KafkaProducer

DISCONNECTED_STATE = (status.ERROR, "Disconnected")
INIT_MESSAGE = "Initializing LiveDataCollector…"


class DataChannel(CounterChannelMixin, PassiveChannel, Moveable):
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
        self._signal: Optional[np.ndarray] = None
        self.arraydesc = ArrayDesc(self.name, shape=(), dtype=np.int32)
        if session.sessiontype != POLLER:
            self._update_status(status.OK, "")

    def doInit(self, mode):
        self._device_selector_obj: Optional[DeviceSelector] = (
            DeviceSelector.parse_device_name(self.device_name, self.workflow_id)
            if self.device_name
            else None
        )

    def doRead(self, maxage=0):
        return [self.curvalue]

    def doReadArray(self, quality):
        return self._signal

    def arrayInfo(self):
        return self.arraydesc

    def doStatus(self, maxage=0):
        return self.curstatus

    def doWriteDeviceName(self, value):
        self._device_selector_obj = DeviceSelector.parse_device_name(
            value, self.workflow_id
        )

    def doWriteWorkflowId(self, value):
        self._workflow_id = value
        # Update device selector if it exists
        if self._device_selector_obj:
            self._device_selector_obj = DeviceSelector(
                device_name=self._device_selector_obj.device_name, workflow_id=value
            )

    def start(self, target=None, **preset):
        # DataChannel is both a Moveable (selector changes) and a PassiveChannel
        # (detector counting).  The two base classes define incompatible start()
        # signatures (positional vs keyword-only), so we must dispatch here.
        if target is not None:
            return Moveable.start(self, target)
        return PassiveChannel.start(self, **preset)

    def doPrepare(self):
        self._update_status(status.BUSY, "Preparing")

        # check if a valid selector is set
        self.curvalue = 0
        self._signal = None
        if not self._device_selector_obj:
            self.log.warning(
                "No workflow channel selected for %s. Will not prepare channel.",
                self.name,
            )
            self._update_status(status.WARN, "No workflow channel selected")
            return

        self._collector.send_workflow_reset_command(self.workflow_id)
        sleep(0.5)  # give backend time to process reset
        self._update_status(status.OK, "")

    def doStop(self):
        self.running = False
        self._update_status(status.OK, "")

    def doFinish(self):
        self.running = False
        self._update_status(status.OK, "")

    def doStart(self, target=None):
        # if no target is given, it's a start command from the Detector class
        # treat it as beginning a count/scan instead of changing selector

        # passivechannel path
        if target is None:
            if not self._device_selector_obj:
                self.log.warning(
                    "No workflow channel selected for %s. Will not start counting.",
                    self.name,
                )
                self._update_status(status.OK, "")
                return
            self.running = True
            self._update_status(status.BUSY, "Counting started")
            return

    def _update_status(self, new_status, message):
        self.curstatus = (new_status, message)
        self._cache.put(self._name, "status", self.curstatus, time.time())

    # Called by collector when a matching DA00 arrives
    def update_data_from_da00(self, da00_msg, timestamp_ns: int):
        if not getattr(self, "running", True):
            return
        try:
            variables = list(da00_msg.data)
            by_name = {
                getattr(v, "name", None): v
                for v in variables
                if getattr(v, "name", None)
            }
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

            # Title from signal label or DA00 result key
            try:
                rk = parse_result_key(da00_msg.source_name)
                fallback_title = rk.output_name or self.name
            except Exception:
                fallback_title = self.name
            title = (getattr(sig, "label", None) or "").strip() or fallback_title
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
            self._update_status(status.BUSY, "Counting")
        except Exception as exc:
            self._update_status(status.ERROR, str(exc))

    def _push_to_nicos(
        self,
        plot_type: str,
        label_arrays: List[np.ndarray],
        timestamp: int,
        *,
        axis_names: Optional[List[str]] = None,
        axis_units: Optional[List[str]] = None,
        title: Optional[str] = None,
        signal_unit: Optional[str] = None,
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

    def _resolve_job(self) -> Optional[JobInfo]:
        """Clean this up and the rest in livedata utils."""
        if not self._collector or not self._selector_obj:
            return None
        sel = self._selector_obj
        reg = self._collector._registry
        if sel.job_number:
            for j in reg.list_jobs():
                if (
                    j.workflow_path == sel.workflow_path
                    and j.source_name == sel.source_name
                    and j.job_number == sel.job_number
                ):
                    return j
            return None
        return reg.resolve_latest(sel.workflow_path, sel.source_name)

    def reset_job(self):
        job = self._resolve_job()
        if job:
            self._collector.send_workflow_reset_command(self.workflow_id)
        else:
            self.log.warning("Could not resolve job to reset")


class LiveDataCollector(Detector):
    """
    One device to:
      * consume DA00 data (KafkaSubscriber with callbacks)
      * tail X5F2 status/heartbeat topics (KafkaConsumer in a small thread)
      * optionally tail responses topic
      * maintain JobRegistry and mirror it into the NICOS cache
      * route DA00 to DataChannel(s) whose 'selector' matches the ResultKey
      * publish JobCommand JSON to commands topic
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
        "responses_topics": Param(
            "Kafka topic(s) where responses/acks are written (optional)",
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
        "service_name": Param(
            "Service name part for command keys (e.g. 'data_reduction')",
            type=str,
            default="data_reduction",
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
    _data_subscriber: Optional[KafkaSubscriber] = None
    _status_consumer: Optional[KafkaConsumer] = None
    _resp_consumer: Optional[KafkaConsumer] = None
    _producer: Optional[KafkaProducer] = None

    def doPreinit(self, mode):
        Detector.doPreinit(self, mode)
        self._registry = JobRegistry()
        self._last_expected_status_time = time.time()
        self._data_subscriber = None

        # Attach collector reference to channels
        for ch in self._channels:
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

        # Responses consumer (optional)
        if self.responses_topics:
            self._resp_consumer = KafkaConsumer.create(
                self.brokers,
                starting_offset="latest",
                group_id=self._unique_group("resp"),
            )
            self._resp_consumer.subscribe(self.responses_topics)
            self._resp_thread = createThread(
                "livedata_responses_tail", self._tail_responses_topic
            )

        # Commands producer
        if self.commands_topic:
            self._producer = KafkaProducer.create(self.brokers)

        self._cache.put(self, "status", (status.WARN, INIT_MESSAGE), time.time())

    def _unique_group(self, label: str) -> str:
        base = self.cfg_group_id or "nicos-livedata"
        return f"{base}-{label}-{uuid4().hex}"

    def _on_data_messages(self, messages: List[Tuple[int, bytes]]):
        for timestamp_ns, raw in messages:
            try:
                if get_schema(raw) != "da00":
                    continue
                da = deserialise_da00(raw)

                # Try to parse as ResultKey (for regular data topics)
                # For NICOS_DATA topic, source_name is just the device name
                try:
                    rk = parse_result_key(da.source_name)
                    self._registry.note_output(
                        rk.workflow_id, rk.job_id, rk.output_name
                    )
                    try:
                        self._registry.mark_seen(
                            rk.job_id.source_name, rk.job_id.job_number
                        )
                    except Exception:
                        pass
                except (json.JSONDecodeError, KeyError, TypeError):
                    # Not a ResultKey JSON, must be a device name from NICOS_DATA topic
                    rk = None

                # Route to matching channels
                self._dispatch_to_channels(timestamp_ns, da)
            except Exception as exc:
                self.log.warning(f"Could not decode/route DA00: {exc}")

        try:
            self._registry.expire_stale()
        except Exception as e:
            self.log.warning(f"Error expiring stale jobs: {e}")

    def _on_no_data(self):
        # Nothing special; do not spam cache.
        pass

    def _tail_status_topic(self):
        """
        Tail X5F2 heartbeat/status messages. We expect msg.status_json containing:
        {
          "status": ...,
          "message": {
            "state": "...",
            "job_id": {"source_name": "...", "job_number": "..."},
            "workflow_id": "instr/ns/name/version",
            "start_time": <ns>, "end_time": <ns>,
            ... (warning/error)
          }
          "update_interval": <ms>
        }
        """
        while True:
            msg = self._status_consumer.poll(timeout_ms=200)
            if not msg:
                time.sleep(0.05)
                self._check_disconnect()
                continue
            try:
                if get_schema(msg.value()) != "x5f2":
                    self._status_consumer._consumer.commit(msg, asynchronous=False)
                    continue
                st = deserialise_x5f2(msg.value())
                js = json.loads(st.status_json) if st.status_json else {}
                payload = js.get("message", js)
                wf_str = payload.get("workflow_id", "")
                wf_parts = wf_str.split("/") if wf_str else []
                if len(wf_parts) == 3:
                    wf = WorkflowId(
                        instrument=wf_parts[0],
                        name=wf_parts[1],
                        version=int(wf_parts[2]),
                    )
                    job = payload.get("job_id", {})
                    self._registry.jobinfo_from_status(
                        wf,
                        job_source_name=job.get("source_name", ""),
                        job_number=job.get("job_number", ""),
                        state=payload.get("state", "unknown"),
                        start_time_ns=payload.get("start_time"),
                        end_time_ns=payload.get("end_time"),
                        heartbeat_ms=st.update_interval,  # NEW
                    )

                # update next expected heartbeat
                self._bump_expected_status(st.update_interval)

                # check if we are in the initializing phase, if we are, set to OK
                if self.status(0) == (status.WARN, INIT_MESSAGE):
                    self._cache.put(self, "status", (status.OK, ""), time.time())

                self._registry.expire_stale()

            except Exception as exc:
                self.log.warning(f"Bad status message: {exc}")
            finally:
                self._status_consumer._consumer.commit(msg, asynchronous=False)

    def _tail_responses_topic(self):
        """
        Examples of a start and stop and reset command response:

        Start:
        {"identifier":{"instrument":"dummy","name":"total_counts","version":1},"job_number":"51d0d89b-d05f-4509-8761-392af404919b","schedule":{"start_time":null,"end_time":null},"aux_source_names":{},"params":{}}
        Stop:
        {"job_id":{"source_name":"panel_0","job_number":"51d0d89b-d05f-4509-8761-392af404919b"},"workflow_id":null,"action":"stop"}
        Reset:
        {"job_id":{"source_name":"panel_0","job_number":"86598705-c030-42b2-8bb4-5a80a7c375aa"},"workflow_id":null,"action":"reset"}

        """

        while True:
            msg = self._resp_consumer.poll(timeout_ms=200)
            if not msg:
                time.sleep(0.05)
                continue
            try:
                raw = msg.value()
                try:
                    js = json.loads(raw.decode("utf-8"))
                except Exception:
                    js = None

                if isinstance(js, dict):
                    # Accept either an ACK of our command or a terminal status
                    action = (js.get("action") or "").lower()
                    job = js.get("job_id") or {}
                    src = job.get("source_name") or js.get("source_name") or ""
                    jn = job.get("job_number") or ""

                    remove_hint = action == "remove"

                    if remove_hint and src and jn:
                        self._registry.remove_job(src, jn)

            except Exception:
                pass
            finally:
                self._resp_consumer._consumer.commit(msg, asynchronous=False)

    def _dispatch_to_channels(self, timestamp_ns: int, da):
        for ch in self._channels:
            dev_sel: Optional[DeviceSelector] = getattr(
                ch, "_device_selector_obj", None
            )

            # Try DeviceSelector (for NICOS_DATA topic)
            if dev_sel and da.source_name:
                if dev_sel.matches_da00_source(da.source_name):
                    ch.update_data_from_da00(da, timestamp_ns)
                    continue

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
            self.log.warning("No producer or commands_topic configured")
            return

        # Build payload according to ADR 0006
        payload = {
            "kind": "job_command",
            "action": "reset",
            "workflow_id": workflow_id,
            "message_id": str(uuid4()),
        }

        wait_for_delivery_event = threading.Event()

        def _on_delivery(err, msg):
            if err:
                self.log.warning(f"Workflow reset command delivery failed: {err}.")
            wait_for_delivery_event.set()

        try:
            self.log.info(f"Sending workflow reset command for {workflow_id}")
            self._producer.produce(
                self.commands_topic,
                message=json.dumps(payload).encode("utf-8"),
                on_delivery_callback=_on_delivery,
            )
            # Wait for delivery confirmation or timeout
            if not wait_for_delivery_event.wait(timeout=5.0):
                self.log.warning("Workflow reset command delivery timed out")
        except Exception as exc:
            self.log.warning(f"Error sending workflow reset command: {exc}")

    def _bump_expected_status(self, update_interval_ms: int):
        interval_s = max(1, int(update_interval_ms // 1000))
        next_due = time.time() + interval_s
        if next_due > self._last_expected_status_time:
            self._last_expected_status_time = next_due

    def _check_disconnect(self):
        if time.time() > (self._last_expected_status_time + self.status_timeout):
            try:
                self._cache.put(self, "status", DISCONNECTED_STATE, time.time())
            except Exception:
                pass

    def doShutdown(self):
        # Best-effort cleanup; Kafka wrappers usually are resilient to late close.
        try:
            if self._data_subscriber:
                self._data_subscriber.close()
        except Exception:
            pass
