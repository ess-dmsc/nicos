from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from uuid import uuid4

import numpy as np
from streaming_data_types.dataarray_da00 import Variable, serialise_da00

from nicos import session
from nicos.core import POLLER, ArrayDesc, Param, anytype, status
from nicos.devices.generic import Detector
from nicos_ess.devices.datasources import livedata
from nicos_ess.devices.datasources.livedata_utils import (
    JobId,
    Selector,
    WorkflowId,
)


def _workflow_id_from_path(workflow_path):
    instrument, namespace, name, version = workflow_path.split("/")
    return WorkflowId(
        instrument=instrument,
        namespace=namespace,
        name=name,
        version=int(version),
    )


def _stable_seed(*parts):
    digest = hashlib.sha256("::".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _infer_template(workflow_path, channel_name=""):
    needle = f"{workflow_path} {channel_name}".lower()
    if any(token in needle for token in ("roi", "tof", "spec", "hist1d")):
        return "1d"
    return "2d"


def _default_workflow_path(channel_name):
    workflow_name = channel_name
    if "roi" not in channel_name.lower() and "xy" not in channel_name.lower():
        workflow_name = f"{channel_name}_xy"
    return f"dummy/detector_data/{workflow_name}/1"


def _parse_update_every(value):
    if isinstance(value, dict):
        magnitude = float(value.get("value", 100.0))
        unit = (value.get("unit") or "ms").lower()
        if unit == "s":
            return int(magnitude * 1000)
        return int(magnitude)
    return int(value)


def _extract_config_updates(config_json):
    if not isinstance(config_json, dict):
        return {}
    items = config_json.get("params", config_json)
    updates = {}
    for key, value in items.items():
        short_key = key.rsplit("/", 1)[-1]
        if short_key in {
            "time_of_arrival_bins",
            "toa_range",
            "pixel_weighting",
            "roi_rectangle",
            "update_every",
        }:
            updates[short_key] = value
    return updates


@dataclass
class _SimulatedLiveJob:
    workflow_id: WorkflowId
    source_name: str
    template: str
    job_number: str = field(default_factory=lambda: str(uuid4()))
    state: str = "active"
    update_every_ms: int = 100
    time_of_arrival_bins: int = 128
    toa_range: dict = field(
        default_factory=lambda: {
            "enabled": False,
            "start": 0.0,
            "stop": 12.0,
            "unit": "ms",
        }
    )
    pixel_weighting: dict = field(
        default_factory=lambda: {"enabled": False, "method": "pixel_number"}
    )
    roi_rectangle: dict = field(
        default_factory=lambda: {
            "x": {"low": 0.25, "high": 0.75},
            "y": {"low": 0.25, "high": 0.75},
        }
    )
    current: np.ndarray | None = None
    cumulative: np.ndarray | None = None
    tick: int = 0
    next_update_s: float = 0.0

    def __post_init__(self):
        self._rng = np.random.default_rng(
            _stable_seed(str(self.workflow_id), self.source_name, self.job_number)
        )
        self.reset()

    @property
    def workflow_path(self):
        return str(self.workflow_id)

    @property
    def job_id(self):
        return JobId(source_name=self.source_name, job_number=self.job_number)

    def reset(self):
        self.tick = 0
        self.current = self._zero_array()
        self.cumulative = self._zero_array()
        self.next_update_s = time.monotonic()

    def apply_updates(self, updates):
        if "time_of_arrival_bins" in updates:
            self.time_of_arrival_bins = int(updates["time_of_arrival_bins"])
        if "toa_range" in updates and isinstance(updates["toa_range"], dict):
            self.toa_range = dict(self.toa_range, **updates["toa_range"])
        if "pixel_weighting" in updates and isinstance(
            updates["pixel_weighting"], dict
        ):
            self.pixel_weighting = dict(
                self.pixel_weighting, **updates["pixel_weighting"]
            )
        if "roi_rectangle" in updates and isinstance(updates["roi_rectangle"], dict):
            self.roi_rectangle = dict(self.roi_rectangle, **updates["roi_rectangle"])
        if "update_every" in updates:
            self.update_every_ms = max(20, _parse_update_every(updates["update_every"]))
        self.reset()

    def advance(self):
        self.tick += 1
        self.current = self._generate_current()
        self.cumulative = self.cumulative + self.current

    def serialised_outputs(self, timestamp_ns):
        self.advance()
        return [
            self._build_da00("current", self.current, timestamp_ns),
            self._build_da00("cumulative", self.cumulative, timestamp_ns),
        ]

    def _shape(self):
        if self.template == "1d":
            return (max(4, int(self.time_of_arrival_bins)),)
        bins = min(max(16, int(self.time_of_arrival_bins)), 192)
        return (bins, bins)

    def _zero_array(self):
        return np.zeros(self._shape(), dtype=np.int32)

    def _generate_current(self):
        if self.template == "1d":
            bins = self._shape()[0]
            x = np.linspace(-1.0, 1.0, bins)
            center = 0.4 * np.sin(self.tick / 10.0)
            profile = np.exp(-0.5 * ((x - center) / 0.22) ** 2)
            lam = 0.5 + 10.0 * profile
            if self.pixel_weighting.get("enabled"):
                lam = lam * (1.0 + np.linspace(0.0, 1.0, bins))
            arr = self._rng.poisson(lam).astype(np.int32)
            roi = self.roi_rectangle or {}
            if roi:
                low = float(roi.get("x", {}).get("low", 0.0))
                high = float(roi.get("x", {}).get("high", 1.0))
                mask = np.zeros_like(arr, dtype=bool)
                start = max(0, int(low * bins))
                stop = min(bins, int(high * bins))
                mask[start:stop] = True
                arr = np.where(mask, arr, 0)
            return arr

        rows, cols = self._shape()
        y = np.linspace(-1.0, 1.0, rows)
        x = np.linspace(-1.0, 1.0, cols)
        yy, xx = np.meshgrid(y, x, indexing="ij")
        center_x = 0.35 * np.sin(self.tick / 12.0)
        center_y = 0.35 * np.cos(self.tick / 14.0)
        profile = np.exp(
            -0.5 * (((xx - center_x) / 0.23) ** 2 + ((yy - center_y) / 0.18) ** 2)
        )
        lam = 0.3 + 7.0 * profile
        if self.pixel_weighting.get("enabled"):
            weights = np.linspace(1.0, 1.6, cols, dtype=np.float64)[None, :]
            lam = lam * weights
        arr = self._rng.poisson(lam).astype(np.int32)
        roi = self.roi_rectangle or {}
        x_low = float(roi.get("x", {}).get("low", 0.0))
        x_high = float(roi.get("x", {}).get("high", 1.0))
        y_low = float(roi.get("y", {}).get("low", 0.0))
        y_high = float(roi.get("y", {}).get("high", 1.0))
        x_start = max(0, int(x_low * cols))
        x_stop = min(cols, int(x_high * cols))
        y_start = max(0, int(y_low * rows))
        y_stop = min(rows, int(y_high * rows))
        mask = np.zeros_like(arr, dtype=bool)
        mask[y_start:y_stop, x_start:x_stop] = True
        return np.where(mask, arr, 0)

    def _build_da00(self, output_name, signal, timestamp_ns):
        source_name = json.dumps(
            {
                "workflow_id": {
                    "instrument": self.workflow_id.instrument,
                    "namespace": self.workflow_id.namespace,
                    "name": self.workflow_id.name,
                    "version": self.workflow_id.version,
                },
                "job_id": {
                    "source_name": self.source_name,
                    "job_number": self.job_number,
                },
                "output_name": output_name,
            }
        )
        label = f"{self.workflow_id.name} {output_name}".strip()

        if self.template == "1d":
            bins = signal.shape[0]
            start = float(self.toa_range.get("start", 0.0))
            stop = float(self.toa_range.get("stop", max(bins, 1)))
            unit = self.toa_range.get("unit", "ms")
            edges = np.linspace(start, stop, bins + 1, dtype=np.float64)
            data = [
                Variable(
                    name="signal",
                    data=signal,
                    shape=signal.shape,
                    axes=["tof"],
                    unit="counts",
                    label=label,
                ),
                Variable(
                    name="tof",
                    data=edges,
                    shape=edges.shape,
                    axes=["tof"],
                    unit=unit,
                    label="TOF",
                ),
            ]
        else:
            rows, cols = signal.shape
            x = np.arange(cols, dtype=np.float64)
            y = np.arange(rows, dtype=np.float64)
            data = [
                Variable(
                    name="signal",
                    data=signal,
                    shape=signal.shape,
                    axes=["y", "x"],
                    unit="counts",
                    label=label,
                ),
                Variable(
                    name="x",
                    data=x,
                    shape=x.shape,
                    axes=["x"],
                    unit="pixel",
                    label="X",
                ),
                Variable(
                    name="y",
                    data=y,
                    shape=y.shape,
                    axes=["y"],
                    unit="pixel",
                    label="Y",
                ),
            ]
        return serialise_da00(
            source_name=source_name,
            timestamp_ns=timestamp_ns,
            data=data,
        )


class _SimulatedLiveBackend:
    def __init__(self, collector):
        self.collector = collector
        self._jobs = {}
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread = None

    def ensure_seeded_jobs(self):
        with self._lock:
            for workflow_path, source_name, template in self._discover_workflows():
                if self._has_active_job(workflow_path, source_name):
                    continue
                workflow_id = _workflow_id_from_path(workflow_path)
                job = _SimulatedLiveJob(
                    workflow_id=workflow_id,
                    source_name=source_name,
                    template=template,
                )
                self._jobs[(source_name, job.job_number)] = job
                self._register_job(job)
        self.collector._push_mapping_to_channels()

    def start(self):
        self.ensure_seeded_jobs()
        self.stop()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def reset_job(self, source_name, job_number):
        with self._lock:
            job = self._jobs.get((source_name, job_number))
            if job:
                job.reset()

    def stop_job(self, source_name, job_number):
        with self._lock:
            job = self._jobs.get((source_name, job_number))
            if job:
                job.state = "stopped"
                self.collector._registry.jobinfo_from_status(
                    job.workflow_id,
                    job_source_name=source_name,
                    job_number=job_number,
                    state="stopped",
                )

    def remove_job(self, source_name, job_number):
        with self._lock:
            self._jobs.pop((source_name, job_number), None)
        self.collector._registry.remove_job(source_name, job_number)
        self.collector._push_mapping_to_channels()

    def apply_workflow_config(self, key_source, config_json):
        updates = _extract_config_updates(config_json)
        if not updates:
            return
        with self._lock:
            for job in self._jobs.values():
                if key_source not in ("", "*") and job.source_name != key_source:
                    continue
                job.apply_updates(updates)

    def _discover_workflows(self):
        discovered = {}
        for channel in self.collector._channels:
            selector = getattr(channel, "_selector_obj", None)
            if selector:
                workflow_path = selector.workflow_path
                source_name = selector.source_name
            else:
                workflow_path = _default_workflow_path(channel.name)
                source_name = "panel_0"
            discovered[(workflow_path, source_name)] = _infer_template(
                workflow_path, channel.name
            )
        if not discovered:
            discovered[("dummy/detector_data/panel_0_xy/1", "panel_0")] = "2d"
        return [
            (workflow_path, source_name, template)
            for (workflow_path, source_name), template in discovered.items()
        ]

    def _has_active_job(self, workflow_path, source_name):
        return any(
            job.workflow_path == workflow_path
            and job.source_name == source_name
            and job.state == "active"
            for job in self._jobs.values()
        )

    def _register_job(self, job):
        now_ns = time.time_ns()
        self.collector._registry.jobinfo_from_status(
            job.workflow_id,
            job_source_name=job.source_name,
            job_number=job.job_number,
            state=job.state,
            start_time_ns=now_ns,
        )
        self.collector._registry.note_output(job.workflow_id, job.job_id, "current")
        self.collector._registry.note_output(job.workflow_id, job.job_id, "cumulative")

    def _run(self):
        while not self._stop_event.is_set():
            next_wait = 0.05
            now = time.monotonic()
            due_messages = []
            with self._lock:
                for job in self._jobs.values():
                    if job.state != "active":
                        continue
                    if now < job.next_update_s:
                        next_wait = min(next_wait, max(job.next_update_s - now, 0.01))
                        continue
                    job.next_update_s = now + job.update_every_ms / 1000.0
                    now_ns = time.time_ns()
                    due_messages.extend(
                        (now_ns, raw) for raw in job.serialised_outputs(now_ns)
                    )
            for timestamp_ns, raw in due_messages:
                self.collector._on_data_messages([(timestamp_ns, raw)])
            self._stop_event.wait(next_wait)


class DataChannel(livedata.DataChannel):
    parameters = dict(
        livedata.DataChannel.parameters,
        curarray=Param(
            "Store the current signal array",
            internal=True,
            type=anytype,
            default=None,
            settable=True,
        ),
        curarraydesc=Param(
            "Store the current signal array description",
            internal=True,
            type=anytype,
            default=None,
            settable=True,
        ),
    )

    def doPreinit(self, mode):
        super().doPreinit(mode)
        self._setROParam("curstatus", (status.OK, ""))
        self._setROParam("curvalue", 0)
        self._setROParam("curarray", None)
        self._setROParam("curarraydesc", self._array_desc.copy())

    def doPrepare(self):
        self._array_desc = ArrayDesc(self.name, shape=(), dtype=np.int32)
        self._setROParam("curarray", None)
        self._setROParam("curarraydesc", self._array_desc.copy())
        super().doPrepare()

    def update_data_from_da00(self, da00_msg, timestamp_ns):
        super().update_data_from_da00(da00_msg, timestamp_ns)
        if self._signal is None:
            return
        self._setROParam("curarray", np.array(self._signal, copy=True, order="C"))
        self._setROParam("curarraydesc", self._array_desc.copy())

    def doReadArray(self, quality):
        del quality
        return self.curarray

    def arrayInfo(self):
        return (self.curarraydesc or self._array_desc,)


class LiveDataCollector(livedata.LiveDataCollector):
    parameters = dict(
        livedata.LiveDataCollector.parameters,
        virtual_items=Param(
            "Store simulated plot selection items",
            internal=True,
            type=anytype,
            default=None,
            settable=True,
        ),
        virtual_mapping=Param(
            "Store simulated plot selection mapping",
            internal=True,
            type=anytype,
            default=None,
            settable=True,
        ),
    )

    hardware_access = False

    def doPreinit(self, mode):
        Detector.doPreinit(self, mode)
        self._registry = livedata.JobRegistry()
        self._last_expected_status_time = time.time()
        self._data_subscriber = None
        self._status_consumer = None
        self._resp_consumer = None
        self._producer = None
        self._dispatch_lock = threading.RLock()
        for channel in self._channels:
            channel._collector = self
        self._sim_backend = None
        self._setROParam("virtual_items", [])
        self._setROParam("virtual_mapping", {})
        if session.sessiontype == POLLER:
            return
        self._sim_backend = _SimulatedLiveBackend(self)
        self._sim_backend.ensure_seeded_jobs()
        self._publish_mapping_state()

    def doPrepare(self):
        if self._sim_backend is not None:
            self._sim_backend.ensure_seeded_jobs()
            self._publish_mapping_state()
        with self._dispatch_lock:
            Detector.doPrepare(self)

    def doStart(self):
        with self._dispatch_lock:
            Detector.doStart(self)
        if self._sim_backend is not None:
            self._sim_backend.start()

    def doFinish(self):
        if self._sim_backend is not None:
            self._sim_backend.stop()
        with self._dispatch_lock:
            Detector.doFinish(self)

    def doStop(self):
        if self._sim_backend is not None:
            self._sim_backend.stop()
        with self._dispatch_lock:
            Detector.doStop(self)

    def send_job_command(
        self,
        *,
        job_id: dict | None = None,
        workflow_id: dict | None = None,
        action: str,
    ):
        del workflow_id
        if not job_id:
            return
        source_name = job_id.get("source_name")
        job_number = job_id.get("job_number")
        if not source_name or not job_number:
            return
        action = action.lower()
        if action == "reset":
            self._sim_backend.reset_job(source_name, job_number)
        elif action == "stop":
            self._sim_backend.stop_job(source_name, job_number)
        elif action == "remove":
            self._sim_backend.remove_job(source_name, job_number)
        self._publish_mapping_state()

    def send_workflow_config(self, *, key_source: str, config_json: dict):
        if self._sim_backend is not None:
            self._sim_backend.apply_workflow_config(key_source, config_json)

    def list_plot_selection_items(self) -> list[dict]:
        if self.virtual_items is not None:
            return self.virtual_items
        return livedata.LiveDataCollector.list_plot_selection_items(self)

    def get_current_mapping(self) -> dict:
        if self.virtual_mapping is not None:
            return self.virtual_mapping
        return livedata.LiveDataCollector.get_current_mapping(self)

    def _publish_mapping_state(self):
        if self._sim_backend is None:
            return
        self._setROParam(
            "virtual_items",
            livedata.LiveDataCollector.list_plot_selection_items(self),
        )
        self._setROParam(
            "virtual_mapping",
            livedata.LiveDataCollector.get_current_mapping(self),
        )

    def doShutdown(self):
        if self._sim_backend is not None:
            self._sim_backend.stop()
