"""
NICOS data source devices for consuming ESSLivedata and sending light commands.

- LiveDataCollector:
    * Subscribes to DA00 data topics
    * Tails X5F2 status/heartbeat topics
    * (optional) Tails responses topics
    * Maintains a JobRegistry and publishes it into NICOS cache
    * Routes DA00 to DataChannel(s) by Selector
    * Provides job_command helpers (reset/stop/remove)

- DataChannel:
    * User selects a "selector" string of the form:
      "<instr>/<ns>/<name>/<version>@<source>#<job_number>/<output>"
    * Receives matched DA00 messages and pushes to NICOS live plots
    * Offers convenience methods reset()/stop()/remove() that send JobCommand
"""

from __future__ import annotations

import json
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
    MASTER,
    POLLER,
    SIMULATION,
    ArrayDesc,
    HasMapping,
    Moveable,
    Override,
    Param,
    Readable,
    anytype,
    dictof,
    host,
    listof,
    oneof,
    status,
    tupleof,
)
from nicos.devices.generic import CounterChannelMixin, Detector, PassiveChannel
from nicos.utils import byteBuffer, createThread, num_sort
from nicos_ess.devices.kafka.consumer import KafkaConsumer, KafkaSubscriber
from nicos_ess.devices.kafka.producer import KafkaProducer

from .livedata_utils import (
    JobInfo,
    JobRegistry,
    Selector,
    WorkflowId,
    parse_result_key,
    parse_selector,
    selector_matches,
)

DISCONNECTED_STATE = (status.ERROR, "Disconnected")
INIT_MESSAGE = "Initializing LiveDataCollector…"


class DataChannel(HasMapping, CounterChannelMixin, PassiveChannel, Moveable):
    """
    Channel that subscribes (via the collector) to a particular workflow/source/job/output
    and forwards DA00 'signal' arrays to NICOS live data. Supports 1D, 2D, and N-D in a
    minimal/robust way.
    """

    parameters = {
        "selector": Param(
            "Selector '<instr>/<ns>/<name>/<ver>@<source>#<job>[/<output>]'",
            type=str,
            default="",
            userparam=True,
            settable=True,
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
    }

    parameter_overrides = {
        "unit": Override(default="events", settable=False, mandatory=False),
        "fmtstr": Override(default="%d"),
        "pollinterval": Override(default=None, userparam=False, settable=False),
        "mapping": Override(
            volatile=True, internal=True, mandatory=False, settable=True
        ),
    }

    def doPreinit(self, mode):
        self._collector = None  # set by LiveDataCollector
        self._selector_obj: Optional[Selector] = (
            parse_selector(self.selector) if self.selector else None
        )
        self._cache.put(self._name, "curstatus", (status.OK, ""), time.time())
        self._signal: Optional[np.ndarray] = None
        self._array_desc = ArrayDesc(self.name, shape=(), dtype=np.int32)
        if mode != SIMULATION:
            self._update_status(status.OK, "")

    def doRead(self, maxage=0):
        return self.curvalue

    def doReadArray(self, quality):
        return self._signal

    def arrayInfo(self):
        return self._array_desc

    def doStatus(self, maxage=0):
        return self.curstatus

    def doWriteSelector(self, value):
        self._selector_obj = parse_selector(value)

    def doWriteMapping(self, mapping):
        self.valuetype = oneof(*sorted(mapping, key=num_sort))

    def doReadMapping(self):
        if not self._collector:
            return {}
        return self._collector.get_current_mapping()

    def doStart(self, target):
        target_value = self.mapping.get(target, "")
        if not target_value:
            raise ValueError(f"Unknown selection '{target}' in mapping")
        self.selector = target_value

    def _update_status(self, new_status, message):
        self.curstatus = (new_status, message)
        self._cache.put(self._name, "status", self.curstatus, time.time())

    # Called by collector when a matching DA00 arrives
    def update_data_from_da00(self, da00_msg, timestamp_ns: int):
        try:
            # Find the 'signal' Variable
            variables = list(da00_msg.data)
            sig = next(
                (v for v in variables if getattr(v, "name", None) == "signal"), None
            )
            if sig is None:
                return

            arr = np.asarray(sig.data)
            self._signal = np.ascontiguousarray(arr, dtype=arr.dtype)
            self.curvalue = int(self._signal.sum()) if self._signal.size else 0

            # Update NICOS array desc
            self._array_desc = ArrayDesc(
                self.name, shape=self._signal.shape, dtype=self._signal.dtype
            )

            # Heuristic plot type
            if self._signal.ndim == 1:
                plot_type = "hist-1d"
                labels = [np.arange(self._signal.shape[0])]
            elif self._signal.ndim == 2:
                plot_type = "hist-2d"
                # NICOS expects x first, y second for label buffers; keep conventional ordering
                labels = [
                    np.arange(self._signal.shape[1]),
                    np.arange(self._signal.shape[0]),
                ]
            else:
                plot_type = "hist-nd"
                labels = [np.arange(self._signal.size)]

            self.poll()  # trigger NICOS data update pipeline
            self._push_to_nicos(plot_type, labels, timestamp_ns)

        except Exception as exc:
            self._update_status(status.ERROR, str(exc))

    def _push_to_nicos(
        self, plot_type: str, label_arrays: List[np.ndarray], timestamp: int
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
                label_shape=tuple(len(l) for l in label_arrays),
                label_dtypes=tuple(l.dtype.str for l in label_arrays),
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

    def doReset(self):
        job = self._resolve_job()
        if job:
            self._collector.send_job_command(
                job_id={"source_name": job.source_name, "job_number": job.job_number},
                action="reset",
            )

    def doStop(self):
        job = self._resolve_job()
        if job:
            self._collector.send_job_command(
                job_id={"source_name": job.source_name, "job_number": job.job_number},
                action="stop",
            )

    def remove(self):
        job = self._resolve_job()
        if job:
            self._collector.send_job_command(
                job_id={"source_name": job.source_name, "job_number": job.job_number},
                action="remove",
            )


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
                rk = parse_result_key(da.source_name)
                # Update job registry with observed output
                self._registry.note_output(rk.workflow_id, rk.job_id, rk.output_name)
                # Route to matching channels
                self._dispatch_to_channels(timestamp_ns, rk, da)
                self._push_mapping_to_channels()
            except Exception as exc:
                self.log.warn(f"Could not decode/route DA00: {exc}")

        # Mirror registry snapshot for UI/clients
        try:
            self._cache.put(
                self, "livedata/jobs", self._registry.list_jobs(), time.time()
            )
        except Exception:
            pass

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
                # parse "instr/ns/name/version" into a minimal WorkflowId
                wf_parts = wf_str.split("/") if wf_str else []
                if len(wf_parts) == 4:
                    wf = WorkflowId(
                        instrument=wf_parts[0],
                        namespace=wf_parts[1],
                        name=wf_parts[2],
                        version=int(wf_parts[3]),
                    )
                    job = payload.get("job_id", {})
                    self._registry.upsert_from_status(
                        wf,
                        job_source_name=job.get("source_name", ""),
                        job_number=job.get("job_number", ""),
                        state=payload.get("state", "unknown"),
                        start_time_ns=payload.get("start_time"),
                        end_time_ns=payload.get("end_time"),
                    )

                # update next expected heartbeat
                self._bump_expected_status(st.update_interval)

                # check if we are in the initializing phase, if we are, set to OK
                if self.status(0) == (status.WARN, INIT_MESSAGE):
                    self._cache.put(self, "status", (status.OK, ""), time.time())

                self._push_mapping_to_channels()

                # mirror into cache
                try:
                    self._cache.put(
                        self, "livedata/jobs", self._registry.list_jobs(), time.time()
                    )
                    self._cache.put(
                        self,
                        "livedata/last_status_json",
                        st.status_json or "",
                        time.time(),
                    )
                except Exception:
                    pass

            except Exception as exc:
                self.log.warn(f"Bad status message: {exc}")
            finally:
                self._status_consumer._consumer.commit(msg, asynchronous=False)

    def _tail_responses_topic(self):
        while True:
            msg = self._resp_consumer.poll(timeout_ms=200)
            if not msg:
                time.sleep(0.05)
                continue
            try:
                # Store last response blob (opaque to NICOS UI unless you parse it further)
                self._cache.put(
                    self, "livedata/last_response", msg.value(), time.time()
                )
            except Exception as exc:
                self.log.warn(f"Bad response message: {exc}")
            finally:
                self._resp_consumer._consumer.commit(msg, asynchronous=False)

    def _dispatch_to_channels(self, timestamp_ns: int, rk, da):
        for ch in self._channels:
            sel: Optional[Selector] = getattr(ch, "_selector_obj", None)
            if not sel:
                continue
            if selector_matches(sel, rk):
                ch.update_data_from_da00(da, timestamp_ns)

    def send_job_command(
        self,
        *,
        job_id: dict | None = None,
        workflow_id: dict | None = None,
        action: str,
    ):
        """
        Publish a JobCommand value JSON to the commands topic.
        Only 'reset' | 'stop' | 'remove' are supported by the backend today.
        """
        if not self._producer or not self.commands_topic:
            self.log.warn("No producer or commands_topic configured")
            return
        payload = {"job_id": job_id, "workflow_id": workflow_id, "action": action}
        # Build a key the backend expects: "<service>/<source|*>/job_command"
        # If we know a job_id with source_name we include it; else '*'.
        src = job_id.get("source_name") if job_id else "*"
        key = f"{self.service_name}/{src}/job_command"
        try:
            self._producer.produce(
                self.commands_topic,
                message=json.dumps(payload).encode("utf-8"),
                key=key,
            )
        except Exception as exc:
            self.log.warn(f"Error sending job_command: {exc}")

    # Optionally expose workflow_config sender for rare cases
    def send_workflow_config(self, *, key_source: str, config_json: dict):
        """
        Send a workflow_config message (rare; the expert UI usually does this).
        key_source is the Kafka 'key' source_name part used by the backend.
        """
        if not self._producer or not self.commands_topic:
            self.log.warn("No producer or commands_topic configured")
            return
        key = f"{self.service_name}/{key_source}/workflow_config"
        try:
            self._producer.produce(
                self.commands_topic,
                message=json.dumps(config_json).encode("utf-8"),
                key=key,
            )
        except Exception as exc:
            self.log.warn(f"Error sending workflow_config: {exc}")

    def list_plot_selection_items(self) -> list[dict]:
        """Return a list of simple, user-friendly plot selections discovered so far.

        Each item looks like:
            {
                "label": "panel_0_xy/current",     # simple for users
                "workflow_name": "panel_0_xy",
                "output": "current",
                "source_name": "panel_0",
                "workflow_path": "dummy/detector_data/panel_0_xy/1",
                "job_number": "<uuid>",
                "selector": "dummy/detector_data/panel_0_xy/1@panel_0#<uuid>/current"
            }

        Also mirrors results into the NICOS cache under:
            - "livedata/plot_selection_items" (list of dicts)
            - "livedata/plot_selections"      (list of simple labels)
        """

        def split_workflow_path(path: str) -> tuple[str, str, str, int]:
            i, ns, n, v = path.split("/")
            return i, ns, n, int(v)

        # Preferred output ordering first
        prefer = ("current", "cumulative")

        def out_sort_key(o: str) -> tuple[int, str]:
            try:
                idx = prefer.index(o)
            except ValueError:
                idx = len(prefer)
            return (idx, o)

        items: list[dict] = []

        for ji in sorted(
            self._registry.list_jobs(),
            key=lambda j: (j.workflow_path, j.source_name, j.job_number),
        ):
            # If we haven't seen any DA00 yet for this job, we won't know outputs.
            outputs = sorted(ji.outputs, key=out_sort_key)
            if not outputs:
                continue

            _, _, wf_name, _ = split_workflow_path(ji.workflow_path)
            for out in outputs:
                label = f"{ji.source_name} ({ji.job_number.split('-')[0]}) {out}"

                selector = f"{ji.workflow_path}@{ji.source_name}#{ji.job_number}/{out}"
                items.append(
                    {
                        "label": label,
                        "workflow_name": wf_name,
                        "output": out,
                        "source_name": ji.source_name,
                        "workflow_path": ji.workflow_path,
                        "job_number": ji.job_number,
                        "selector": selector,
                    }
                )

        # Mirror to NICOS cache for poller/daemon sharing
        try:
            now = time.time()
            self._cache.put(self, "livedata/plot_selection_items", items, now)
            self._cache.put(
                self, "livedata/plot_selections", [i["label"] for i in items], now
            )
        except Exception:
            pass

        return items

    def list_plot_selections(self) -> list[str]:
        """Return a flat list of simple labels like 'panel_0_xy/current'.

        This is a convenience wrapper around list_plot_selection_items() and also
        refreshes the cache keys.
        """
        items = self.list_plot_selection_items()
        return [i["label"] for i in items]

    def _bump_expected_status(self, update_interval_ms: int):
        interval_s = max(1, int(update_interval_ms // 1000))
        next_due = time.time() + interval_s
        if next_due > self._last_expected_status_time:
            self._last_expected_status_time = next_due

    def _push_mapping_to_channels(self):
        """Build a label->selector mapping and write it to every channel's 'mapping'."""
        # reuse your existing discovery and keep labels minimal
        mapping = self.get_current_mapping()
        for ch in self._channels:
            if isinstance(ch, DataChannel):
                try:
                    ch.mapping = mapping
                except Exception:
                    self.log.warn(f"Could not update mapping for channel {ch.name}")

    def get_current_mapping(self) -> dict:
        """Return the current label->selector mapping as built for channels."""
        items = self.list_plot_selection_items()
        return {it["label"]: it["selector"] for it in items}

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
