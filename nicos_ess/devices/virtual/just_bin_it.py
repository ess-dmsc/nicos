import hashlib
import json
import threading
import time
from dataclasses import dataclass

import numpy as np
from streaming_data_types import serialise_hs00, serialise_hs01

from nicos.core import ArrayDesc, Param, status, tupleof
from nicos.devices.generic import Detector
from nicos_ess.devices.datasources import just_bin_it as jbi

serialiser_by_schema = {
    "hs00": serialise_hs00,
    "hs01": serialise_hs01,
}


def _stable_seed(*parts):
    digest = hashlib.sha256("::".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _roi_height(image):
    return max(len(image.left_edges), 1)


def _image_shape(image):
    if image.hist_type == "1-D TOF":
        return (int(image.num_bins),)
    if image.hist_type == "2-D TOF":
        bins = int(image.num_bins)
        return (bins, bins)
    if image.hist_type == "2-D DET":
        return (int(image.det_width), int(image.det_height))
    if image.hist_type == "2-D ROI":
        return (int(image.det_width), _roi_height(image))
    raise ValueError(f"Unsupported histogram type {image.hist_type}")


def _arraydesc_for_image(image):
    shape = _image_shape(image)
    return ArrayDesc(image.name, shape=shape, dtype=np.float64)


def _zero_data_for_image(image):
    return np.zeros(shape=_image_shape(image), dtype=np.float64)


def _metadata_for_image(image):
    if image.hist_type == "1-D TOF":
        start, stop = image.tof_range
        edges = np.linspace(start, stop, int(image.num_bins) + 1, dtype=np.int64)
        return [
            {
                "length": int(image.num_bins),
                "bin_boundaries": edges,
                "unit": "ns",
                "label": "tof",
            }
        ]
    if image.hist_type == "2-D TOF":
        start, stop = image.tof_range
        edges = np.linspace(start, stop, int(image.num_bins) + 1, dtype=np.int64)
        return [
            {
                "length": int(image.num_bins),
                "bin_boundaries": edges,
                "unit": "ns",
                "label": "tof_x",
            },
            {
                "length": int(image.num_bins),
                "bin_boundaries": edges,
                "unit": "ns",
                "label": "tof_y",
            },
        ]
    if image.hist_type == "2-D DET":
        x_edges = np.linspace(
            image.det_range[0],
            image.det_range[1],
            int(image.det_width) + 1,
            dtype=np.int64,
        )
        y_edges = np.linspace(
            image.det_range[0],
            image.det_range[1],
            int(image.det_height) + 1,
            dtype=np.int64,
        )
        return [
            {
                "length": int(image.det_width),
                "bin_boundaries": x_edges,
                "unit": "",
                "label": "det_x",
            },
            {
                "length": int(image.det_height),
                "bin_boundaries": y_edges,
                "unit": "",
                "label": "det_y",
            },
        ]
    if image.hist_type == "2-D ROI":
        x_edges = np.linspace(
            image.det_range[0],
            image.det_range[1],
            int(image.det_width) + 1,
            dtype=np.int64,
        )
        left_edges = list(image.left_edges or [0])
        y_edges = np.array(left_edges + [left_edges[-1] + 1], dtype=np.int64)
        return [
            {
                "length": int(image.det_width),
                "bin_boundaries": x_edges,
                "unit": "",
                "label": "det_x",
            },
            {
                "length": _roi_height(image),
                "bin_boundaries": y_edges,
                "unit": "",
                "label": "roi",
            },
        ]
    raise ValueError(f"Unsupported histogram type {image.hist_type}")


def _config_fingerprint(image):
    return (
        image.hist_type,
        tuple(image.tof_range),
        tuple(image.det_range),
        int(image.det_width),
        int(image.det_height),
        int(image.num_bins),
        tuple(image.left_edges),
        image.source,
    )


@dataclass
class _HistogramState:
    fingerprint: tuple
    data: np.ndarray
    rng: np.random.Generator
    ticks: int = 0


class _NoopSubscriber:
    def subscribe(self, topics, callback):
        del topics, callback

    def stop_consuming(self):
        return None

    def close(self):
        return None


class _SimulatedJustBinItRun:
    def __init__(self, detector):
        self.detector = detector
        self._states = {}
        self._lock = threading.RLock()
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        self.stop(emit_final=False)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, emit_final=True):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        if emit_final:
            for image in self.detector._attached_images:
                state = self._state_for(image)
                if state is not None:
                    self._emit(image, state, "FINISHED")

    def reset(self):
        with self._lock:
            self._states = {}

    def _state_for(self, image):
        with self._lock:
            fingerprint = _config_fingerprint(image)
            state = self._states.get(image.name)
            if state is not None and state.fingerprint == fingerprint:
                return state
            state = _HistogramState(
                fingerprint=fingerprint,
                data=_zero_data_for_image(image),
                rng=np.random.default_rng(
                    _stable_seed(self.detector.name, image.name, fingerprint)
                ),
            )
            self._states[image.name] = state
            return state

    def _run(self):
        interval = max(0.05, min(float(self.detector.liveinterval) / 4.0, 0.2))
        while not self._stop_event.wait(interval):
            for image in self.detector._attached_images:
                state = self._state_for(image)
                state.data = state.data + self._increment(image, state)
                state.ticks += 1
                self._emit(image, state, "COUNTING")

    def _increment(self, image, state):
        if image.hist_type == "1-D TOF":
            bins = int(image.num_bins)
            x = np.linspace(-1.0, 1.0, bins)
            center = 0.35 * np.sin(state.ticks / 12.0)
            profile = np.exp(-0.5 * ((x - center) / 0.2) ** 2)
            return state.rng.poisson(1.0 + 5.0 * profile).astype(np.float64)

        if image.hist_type == "2-D TOF":
            bins = int(image.num_bins)
            axis = np.linspace(-1.0, 1.0, bins)
            xx, yy = np.meshgrid(axis, axis, indexing="ij")
            center_x = 0.35 * np.sin(state.ticks / 15.0)
            center_y = 0.35 * np.cos(state.ticks / 17.0)
            profile = np.exp(
                -0.5 * (((xx - center_x) / 0.22) ** 2 + ((yy - center_y) / 0.22) ** 2)
            )
            return state.rng.poisson(0.8 + 4.0 * profile).astype(np.float64)

        if image.hist_type == "2-D DET":
            width, height = _image_shape(image)
            x = np.linspace(-1.0, 1.0, width)
            y = np.linspace(-1.0, 1.0, height)
            xx, yy = np.meshgrid(x, y, indexing="ij")
            profile = np.exp(-0.5 * (((xx / 0.35) ** 2) + ((yy / 0.2) ** 2)))
            weight = 1.0 + 0.1 * np.sin(state.ticks / 20.0)
            return state.rng.poisson(0.6 + 3.5 * weight * profile).astype(np.float64)

        width, height = _image_shape(image)
        x = np.linspace(-1.0, 1.0, width)
        y = np.linspace(-1.0, 1.0, height)
        xx, yy = np.meshgrid(x, y, indexing="ij")
        profile = np.exp(-0.5 * (((xx / 0.4) ** 2) + ((yy / 0.35) ** 2)))
        return state.rng.poisson(0.5 + 3.0 * profile).astype(np.float64)

    def _emit(self, image, state, state_name):
        serialise = serialiser_by_schema[self.detector.hist_schema]
        payload = {
            "source": image.name,
            "timestamp": int(time.time() * 1000),
            "current_shape": list(state.data.shape),
            "dim_metadata": _metadata_for_image(image),
            "data": np.ascontiguousarray(state.data),
            "info": json.dumps(
                {
                    "id": image._unique_id,
                    "state": state_name,
                    "rate": float(state.data.sum()),
                }
            ),
        }
        image.new_messages_callback([(time.time_ns(), serialise(payload))])


class JustBinItImage(jbi.JustBinItImage):
    parameters = {
        "curstatus": Param(
            "Store the current device status",
            internal=True,
            type=tupleof(int, str),
            settable=True,
        ),
        "curvalue": Param(
            "Store the current histogram sum",
            internal=True,
            type=int,
            default=0,
            settable=True,
        ),
    }

    def doPreinit(self, mode):
        self._unique_id = None
        self._current_status = (status.OK, "")
        self._kafka_subscriber = _NoopSubscriber()
        self._hist_edges = np.array([])
        self._setROParam("curstatus", self._current_status)
        self._setROParam("curvalue", 0)
        self._setROParam("event_rate", 0.0)

    def doInit(self, mode):
        self._hist_sum = 0
        self._zero_data()

    @property
    def arraydesc(self):
        return _arraydesc_for_image(self)

    def _zero_data(self):
        self._hist_data = _zero_data_for_image(self)

    def doPrepare(self):
        self._update_status(status.BUSY, "Preparing")
        self._zero_data()
        self._hist_edges = np.array([])
        self._hist_sum = 0
        self._setROParam("curvalue", 0)
        self._setROParam("event_rate", 0.0)
        self._update_status(status.OK, "")

    def new_messages_callback(self, messages):
        super().new_messages_callback(messages)
        self._setROParam("curvalue", int(self._hist_sum))
        self._setROParam("event_rate", float(self.event_rate))

    def _update_status(self, new_status, message):
        self._current_status = (new_status, message)
        self._setROParam("curstatus", self._current_status)

    def doRead(self, maxage=0):
        return [self.curvalue]

    def doReadArray(self, quality):
        return self._hist_data

    def doStatus(self, maxage=0):
        return self.curstatus

    def doShutdown(self):
        self._update_status(status.OK, "")


class JustBinItDetector(jbi.JustBinItDetector):
    hardware_access = False

    def doPreinit(self, mode):
        Detector.doPreinit(self, mode)
        self._ack_thread = None
        self._exit_thread = False
        self._histogramming_started = False
        self._stop_requested = False
        self._sim_run = _SimulatedJustBinItRun(self)

    def doPrepare(self):
        self._exit_thread = False
        self._ack_thread = None
        self._histogramming_started = False
        self._stop_requested = False
        self._sim_run.stop(emit_final=False)
        self._sim_run.reset()
        Detector.doPrepare(self)

    def doStart(self, **preset):
        unique_id = f"nicos-{self.name}-{int(time.time())}"
        self._create_config(unique_id)
        Detector.doStart(self)
        self._histogramming_started = True
        self._sim_run.start()

    def _request_histogram_stop(self):
        if not self._histogramming_started or self._stop_requested:
            return
        self._stop_requested = True
        self._sim_run.stop(emit_final=True)

    def doShutdown(self):
        self._do_stop()

    def _send_command(self, topic, message):
        pass
