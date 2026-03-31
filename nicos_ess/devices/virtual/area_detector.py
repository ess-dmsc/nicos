import hashlib
import threading
import time
from dataclasses import dataclass

import numpy as np

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    ArrayDesc,
    Override,
    Param,
    oneof,
    status,
    tupleof,
)
from nicos.devices.generic import ActiveChannel, ImageChannelMixin
from nicos.utils import createThread
from nicos_ess.devices.epics import area_detector as epics_area_detector

binning_factor_map = epics_area_detector.binning_factor_map
ImageMode = epics_area_detector.ImageMode
ImageType = epics_area_detector.ImageType
PROJECTION = epics_area_detector.PROJECTION
FLATFIELD = epics_area_detector.FLATFIELD
DARKFIELD = epics_area_detector.DARKFIELD
INVALID = epics_area_detector.INVALID
AreaDetectorCollector = epics_area_detector.AreaDetectorCollector
AreaDetectorAcquisitionMixin = epics_area_detector.AreaDetectorAcquisitionMixin


def _stable_seed(name):
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


@dataclass(frozen=True)
class _SimulatorSnapshot:
    image_mode: str
    binning: str
    max_sizex: int
    max_sizey: int
    sizex: int
    sizey: int
    startx: int
    starty: int
    acquiretime: float
    acquireperiod: float
    num_images: int
    image_counter: int
    status: tuple[int, str]
    image: np.ndarray


class FakeAreaDetector:
    def __init__(self, *, seed):
        self._state_lock = threading.RLock()
        self._rng = np.random.default_rng(seed)
        self._image_mode = "single"
        self._binning = "1x1"
        self._max_sizex = 1024
        self._max_sizey = 1024
        self._sizex = 1024
        self._sizey = 1024
        self._startx = 0
        self._starty = 0
        self._acquiretime = 0.1
        self._acquireperiod = 1.0
        self._num_images = 1
        self._image_counter = 0
        self._status = (status.OK, "Done")
        self._image = np.zeros((self._max_sizey, self._max_sizex), dtype=np.uint16)
        self._callback = None
        self._status_callback = None
        self._stop_event = threading.Event()
        self._running_flag = threading.Event()
        self._run_thread = threading.Thread(target=self._run, daemon=True)
        self._status_thread = threading.Thread(target=self._update_status, daemon=True)
        self._run_thread.start()
        self._status_thread.start()

    def register_callback(self, callback):
        self._callback = callback

    def register_status_callback(self, callback):
        self._status_callback = callback

    def _emit_status(self):
        callback = self._status_callback
        if callback is not None:
            callback()

    def _emit_image(self):
        callback = self._callback
        if callback is not None:
            callback()

    def snapshot(self):
        with self._state_lock:
            return _SimulatorSnapshot(
                image_mode=self._image_mode,
                binning=self._binning,
                max_sizex=self._max_sizex,
                max_sizey=self._max_sizey,
                sizex=self._sizex,
                sizey=self._sizey,
                startx=self._startx,
                starty=self._starty,
                acquiretime=self._acquiretime,
                acquireperiod=self._acquireperiod,
                num_images=self._num_images,
                image_counter=self._image_counter,
                status=self._status,
                image=self._image,
            )

    def set_geometry(self, *, sizex=None, sizey=None, startx=None, starty=None):
        with self._state_lock:
            if sizex is not None:
                self._sizex = int(sizex)
            if sizey is not None:
                self._sizey = int(sizey)
            if startx is not None:
                self._startx = int(startx)
            if starty is not None:
                self._starty = int(starty)

    def set_timing(self, *, acquiretime=None, acquireperiod=None):
        with self._state_lock:
            if acquiretime is not None:
                self._acquiretime = float(acquiretime)
            if acquireperiod is not None:
                self._acquireperiod = float(acquireperiod)

    def set_mode(self, *, image_mode=None, num_images=None, binning=None):
        with self._state_lock:
            if image_mode is not None:
                self._image_mode = str(image_mode)
            if num_images is not None:
                self._num_images = int(num_images)
            if binning is not None:
                self._binning = str(binning)

    def set_test_state(self, *, image=None, image_counter=None, detector_status=None):
        with self._state_lock:
            if image is not None:
                self._image = np.ascontiguousarray(image)
            if image_counter is not None:
                self._image_counter = int(image_counter)
            if detector_status is not None:
                self._status = detector_status
        if detector_status is not None:
            self._emit_status()

    def shutdown(self):
        self._stop_event.set()
        self._running_flag.clear()
        self._run_thread.join(timeout=1.0)
        self._status_thread.join(timeout=1.0)

    def _set_status(self, detector_status):
        with self._state_lock:
            self._status = detector_status
        self._emit_status()

    def acquire(self):
        with self._state_lock:
            self._running_flag.set()
            self._image_counter = 0
            self._status = (status.BUSY, "Acquiring")
        self._emit_status()

    def stop(self):
        self._running_flag.clear()
        self._set_status((status.OK, "Done"))

    def _update_status(self):
        while not self._stop_event.is_set():
            snapshot = self.snapshot()
            if self._running_flag.is_set():
                if snapshot.status[0] != status.ERROR:
                    self._set_status((status.BUSY, "Acquiring"))
                else:
                    self._emit_status()
            elif snapshot.status[0] == status.BUSY:
                self._set_status((status.OK, "Done"))
            else:
                self._emit_status()
            self._stop_event.wait(1.0)

    def _run(self):
        while not self._stop_event.is_set():
            if not self._running_flag.is_set():
                self._stop_event.wait(0.01)
                continue

            snapshot = self.snapshot()
            if self._stop_event.wait(snapshot.acquireperiod):
                break

            try:
                image = self._generate_image(snapshot)
            except ValueError as error:
                self._running_flag.clear()
                self._set_status((status.ERROR, str(error)))
                continue

            with self._state_lock:
                self._image = np.ascontiguousarray(
                    image.astype(np.uint16, copy=False).ravel()
                )
                self._image_counter += 1
                image_counter = self._image_counter
                image_mode = self._image_mode
                num_images = self._num_images
            self._emit_image()

            if image_mode == "single":
                self._running_flag.clear()
                self._set_status((status.OK, "Done"))
            elif image_mode == "multiple" and image_counter >= num_images:
                self._running_flag.clear()
                self._set_status((status.OK, "Done"))

    def _generate_image(self, snapshot):
        if snapshot.sizex < 0 or snapshot.sizey < 0:
            raise ValueError("Image size must be >= 0")
        if snapshot.startx < 0 or snapshot.starty < 0:
            raise ValueError("Image start offsets must be >= 0")
        if snapshot.startx + snapshot.sizex > snapshot.max_sizex:
            raise ValueError("Image X range exceeds detector bounds")
        if snapshot.starty + snapshot.sizey > snapshot.max_sizey:
            raise ValueError("Image Y range exceeds detector bounds")

        binning_factor = int(snapshot.binning[0])
        if binning_factor > 1 and (
            snapshot.sizex % binning_factor or snapshot.sizey % binning_factor
        ):
            raise ValueError("Image size must be divisible by the binning factor")

        y = np.linspace(0, snapshot.max_sizey - 1, snapshot.max_sizey)
        x = np.linspace(0, snapshot.max_sizex - 1, snapshot.max_sizex)
        x, y = np.meshgrid(x, y)

        center_x = snapshot.max_sizex / 2
        center_y = snapshot.max_sizey / 2 + snapshot.max_sizey * 0.1
        sigma_x = snapshot.max_sizex / 8
        sigma_y = snapshot.max_sizey / 4

        image = np.exp(
            -(
                ((x - center_x) ** 2) / (2 * sigma_x**2)
                + ((y - center_y) ** 2) / (2 * sigma_y**2)
            )
        )
        image += np.abs(self._rng.normal(0, 0.1, image.shape))
        image *= 100 * snapshot.acquiretime
        image *= self._rng.uniform(0.8, 1.2)

        image = image[
            snapshot.starty : snapshot.starty + snapshot.sizey,
            snapshot.startx : snapshot.startx + snapshot.sizex,
        ]
        if binning_factor > 1 and image.size:
            image = image.reshape(
                snapshot.sizey // binning_factor,
                binning_factor,
                snapshot.sizex // binning_factor,
                binning_factor,
            ).mean(axis=(1, 3))
        return image


class AreaDetector(AreaDetectorAcquisitionMixin, ImageChannelMixin, ActiveChannel):
    """
    Virtual area detector with an in-process simulator and shared acquisition
    semantics matching the EPICS-backed area detector implementation.
    """

    parameters = {
        "imagemode": Param(
            "Mode to acquire images.",
            type=oneof("single", "multiple", "continuous"),
            settable=True,
            default="continuous",
            volatile=False,
        ),
        "binning": Param(
            "Binning factor",
            type=oneof("1x1", "2x2", "4x4"),
            settable=True,
            default="1x1",
            volatile=False,
        ),
        "sizex": Param(
            "Image X size.", settable=True, volatile=False, type=int, default=1024
        ),
        "sizey": Param(
            "Image Y size.", settable=True, volatile=False, type=int, default=1024
        ),
        "startx": Param(
            "Image X start index.", settable=True, volatile=False, type=int, default=0
        ),
        "starty": Param(
            "Image Y start index.", settable=True, volatile=False, type=int, default=0
        ),
        "acquiretime": Param(
            "Exposure time ", settable=True, volatile=False, default=0.1
        ),
        "acquireperiod": Param(
            "Time between exposure starts.", settable=True, volatile=False, default=1.0
        ),
        "numimages": Param(
            "Number of images to take (only in imageMode=multiple).",
            settable=True,
            volatile=False,
            type=int,
            default=1,
        ),
        "curstatus": Param(
            "Store the current device status",
            internal=True,
            type=tupleof(int, str),
            settable=True,
        ),
        "curvalue": Param(
            "Store the current image counter",
            internal=True,
            type=int,
            default=0,
            settable=True,
        ),
    }

    parameter_overrides = {
        "presetaliases": Override(default=["n"], mandatory=False),
    }

    hardware_access = False

    def doPreinit(self, mode):
        self._init_acquisition_state()
        self._current_status = (status.OK, "")
        self._setROParam("curstatus", self._current_status)
        self._setROParam("curvalue", 0)

        self._ad_simulator = None
        if session.sessiontype != POLLER:
            self._ad_simulator = FakeAreaDetector(seed=_stable_seed(self.name))
            self._configure_simulator_from_params()
            if mode != SIMULATION:
                self._ad_simulator.register_callback(self.on_image_callback)
                self._ad_simulator.register_status_callback(self.on_status_callback)

    def doInit(self, mode):
        self.update_arraydesc()
        self._image_array = np.zeros(self.arraydesc.shape, dtype=self.arraydesc.dtype)

    def _configure_simulator_from_params(self):
        if self._ad_simulator is None:
            return
        self._ad_simulator.set_geometry(
            sizex=int(self.sizex),
            sizey=int(self.sizey),
            startx=int(self.startx),
            starty=int(self.starty),
        )
        self._ad_simulator.set_timing(
            acquiretime=self.acquiretime,
            acquireperiod=self.acquireperiod,
        )
        self._ad_simulator.set_mode(
            image_mode=self.imagemode,
            num_images=int(self.numimages),
            binning=self.binning,
        )

    def _update_status(self, new_status, message):
        self._current_status = (new_status, message)
        self._setROParam("curstatus", self._current_status)

    def _update_counter(self, image_count):
        self._setROParam("curvalue", int(image_count))

    def _simulator_snapshot(self):
        if self._ad_simulator is None:
            return None
        return self._ad_simulator.snapshot()

    def on_status_callback(self):
        snapshot = self._simulator_snapshot()
        if snapshot is None:
            return
        self._update_status(*snapshot.status)
        self._update_counter(snapshot.image_counter)

    def on_image_callback(self):
        snapshot = self._simulator_snapshot()
        if snapshot is None:
            return
        self._update_status(*snapshot.status)
        self._update_counter(snapshot.image_counter)
        if time.monotonic() >= self._last_update + self._plot_update_delay:
            createThread(f"get_image_{time.time_ns()}", self.get_image)

    def _read_image_counter(self, maxage=0):
        snapshot = self._simulator_snapshot()
        if snapshot is not None:
            return snapshot.image_counter
        return int(self.curvalue)

    def _read_detector_status(self, maxage=0):
        snapshot = self._simulator_snapshot()
        if snapshot is not None:
            return snapshot.status
        return self.curstatus

    def _fetch_image_array(self):
        snapshot = self._simulator_snapshot()
        if snapshot is not None:
            return snapshot.image
        return self._image_array

    def update_arraydesc(self):
        shape = (int(self.sizey), int(self.sizex))
        binning_factor = int(self.binning[0])
        shape = (shape[0] // binning_factor, shape[1] // binning_factor)
        self._update_plot_delay(shape)
        self.arraydesc = ArrayDesc(self.name, shape=shape, dtype=np.uint16)

    def doStatus(self, maxage=0):
        return self._read_detector_status()

    def doStart(self):
        num_images = self._requested_image_count()
        if num_images == 0:
            return

        if self._ad_simulator is not None:
            if num_images is None:
                self._ad_simulator.set_mode(image_mode="continuous")
            elif num_images == 1:
                self._ad_simulator.set_mode(image_mode="single", num_images=1)
            else:
                self._ad_simulator.set_mode(
                    image_mode="multiple",
                    num_images=int(num_images),
                )

        if not self._start_acquisition_cycle():
            return
        if self._ad_simulator is not None:
            self._ad_simulator.acquire()

    def doStop(self):
        if self._ad_simulator is not None:
            self._ad_simulator.stop()

    def _limit_size(self, value, max_value):
        if value > max_value:
            value = max_value
        return int(value)

    def _limit_start(self, value):
        if value < 0:
            value = 0
        return int(value)

    def doReadSizex(self):
        snapshot = self._simulator_snapshot()
        return snapshot.sizex if snapshot is not None else int(self.sizex)

    def doWriteSizex(self, value):
        value = self._limit_size(value, self.maxsizex)
        if self._ad_simulator is not None:
            self._ad_simulator.set_geometry(sizex=value)

    def doReadSizey(self):
        snapshot = self._simulator_snapshot()
        return snapshot.sizey if snapshot is not None else int(self.sizey)

    def doWriteSizey(self, value):
        value = self._limit_size(value, self.maxsizey)
        if self._ad_simulator is not None:
            self._ad_simulator.set_geometry(sizey=value)

    def doReadStartx(self):
        snapshot = self._simulator_snapshot()
        return snapshot.startx if snapshot is not None else int(self.startx)

    def doWriteStartx(self, value):
        value = self._limit_start(value)
        if self._ad_simulator is not None:
            self._ad_simulator.set_geometry(startx=value)

    def doReadStarty(self):
        snapshot = self._simulator_snapshot()
        return snapshot.starty if snapshot is not None else int(self.starty)

    def doWriteStarty(self, value):
        value = self._limit_start(value)
        if self._ad_simulator is not None:
            self._ad_simulator.set_geometry(starty=value)

    def doReadAcquiretime(self):
        snapshot = self._simulator_snapshot()
        return snapshot.acquiretime if snapshot is not None else float(self.acquiretime)

    def doWriteAcquiretime(self, value):
        if self._ad_simulator is not None:
            self._ad_simulator.set_timing(acquiretime=value)

    def doReadAcquireperiod(self):
        snapshot = self._simulator_snapshot()
        if snapshot is not None:
            return snapshot.acquireperiod
        return float(self.acquireperiod)

    def doWriteAcquireperiod(self, value):
        if self._ad_simulator is not None:
            self._ad_simulator.set_timing(acquireperiod=value)

    def doReadNumimages(self):
        snapshot = self._simulator_snapshot()
        return snapshot.num_images if snapshot is not None else int(self.numimages)

    def doWriteNumimages(self, value):
        if self._ad_simulator is not None:
            self._ad_simulator.set_mode(num_images=int(value))

    def doWriteImagemode(self, value):
        if self._ad_simulator is not None:
            self._ad_simulator.set_mode(image_mode=value)

    def doReadImagemode(self):
        snapshot = self._simulator_snapshot()
        return snapshot.image_mode if snapshot is not None else self.imagemode

    def doReadBinning(self):
        snapshot = self._simulator_snapshot()
        return snapshot.binning if snapshot is not None else self.binning

    def doWriteBinning(self, value):
        if self._ad_simulator is not None:
            self._ad_simulator.set_mode(binning=value)

    def get_topic_and_source(self):
        return "some_topic", "some_source"

    @property
    def maxsizex(self):
        snapshot = self._simulator_snapshot()
        return snapshot.max_sizex if snapshot is not None else 1024

    @property
    def maxsizey(self):
        snapshot = self._simulator_snapshot()
        return snapshot.max_sizey if snapshot is not None else 1024

    def doShutdown(self):
        if self._ad_simulator is not None:
            self._ad_simulator.shutdown()
