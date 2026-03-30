import threading
import time

import numpy as np

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    ArrayDesc,
    Override,
    Param,
    anytype,
    oneof,
    status,
    tupleof,
)
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


class FakeAreaDetector:
    def __init__(self):
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
        self._callback = None
        self._status_callback = None
        self._run_thread = threading.Thread(target=self._run, daemon=True)
        self._status_thread = threading.Thread(target=self._update_status, daemon=True)
        self._running_flag = threading.Event()
        self._running_flag.clear()
        self._run_thread.start()
        self._status_thread.start()
        self._status = (status.OK, "Done")
        self._image = np.zeros((self._max_sizey, self._max_sizex), dtype=np.uint16)

    def register_callback(self, callback):
        self._callback = callback

    def register_status_callback(self, callback):
        self._status_callback = callback

    def _emit_status(self):
        if self._status_callback is not None:
            self._status_callback()

    def _update_status(self):
        while True:
            if self._running_flag.is_set():
                self._status = (status.BUSY, "Acquiring")
            else:
                self._status = (status.OK, "Done")
            self._emit_status()
            time.sleep(1.0)

    def acquire(self):
        self._running_flag.set()
        self._image_counter = 0
        self._status = (status.BUSY, "Acquiring")
        self._emit_status()

    def stop(self):
        self._running_flag.clear()
        self._status = (status.OK, "Done")
        self._emit_status()

    def _run(self):
        while True:
            if self._running_flag.is_set():
                self._status = (status.BUSY, "Acquiring")
                self._emit_status()
                time.sleep(self._acquireperiod)
                self._gen_image()
                self._emit_status()

                if self._image_mode == "single":
                    self._running_flag.clear()
                    self._status = (status.OK, "Done")
                    self._emit_status()
                elif self._image_mode == "multiple":
                    if self._image_counter >= self._num_images:
                        self._running_flag.clear()
                        self._status = (status.OK, "Done")
                        self._emit_status()
            else:
                self._status = (status.OK, "Done")

            time.sleep(0.01)

    def _gen_image(self):
        y = np.linspace(0, self._max_sizey - 1, self._max_sizey)
        x = np.linspace(0, self._max_sizex - 1, self._max_sizex)
        x, y = np.meshgrid(x, y)

        center_x = self._max_sizex / 2
        center_y = self._max_sizey / 2 + self._max_sizey * 0.1
        sigma_x = self._max_sizex / 8
        sigma_y = self._max_sizey / 4

        image = np.exp(
            -(
                ((x - center_x) ** 2) / (2 * sigma_x**2)
                + ((y - center_y) ** 2) / (2 * sigma_y**2)
            )
        )
        image += np.abs(np.random.normal(0, 0.1, image.shape))
        image *= 100 * self._acquiretime
        image *= np.random.uniform(0.8, 1.2)

        try:
            image = image[
                self._starty : self._starty + self._sizey,
                self._startx : self._startx + self._sizex,
            ]
        except Exception:
            return

        binning_factor = int(self._binning[0])
        if binning_factor > 1:
            image = image.reshape(
                self._sizey // binning_factor,
                binning_factor,
                self._sizex // binning_factor,
                binning_factor,
            ).mean(axis=(1, 3))

        self._image = image.astype(np.uint16, copy=False).ravel()
        self._image_counter += 1
        if self._callback:
            self._callback()


class AreaDetector(epics_area_detector.AreaDetector):
    """
    Virtual area detector that reuses the shared area detector logic while
    replacing EPICS transport with an in-process simulator.
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
        "curarray": Param(
            "Store the current detector image",
            internal=True,
            type=anytype,
            default=None,
            settable=True,
        ),
    }

    parameter_overrides = dict(
        epics_area_detector.AreaDetector.parameter_overrides,
        pv_root=Override(default="SIM:AD:", mandatory=False, userparam=False),
        image_pv=Override(default="SIM:AD:IMAGE", mandatory=False, userparam=False),
    )

    hardware_access = False

    def doPreinit(self, mode):
        self._image_processing_lock = threading.RLock()
        self._ad_simulator = FakeAreaDetector()
        self._initialize_ad_simulator()
        self._setROParam("curstatus", (status.OK, ""))
        self._setROParam("curvalue", 0)
        if mode == SIMULATION:
            return
        if session.sessiontype != POLLER:
            self._ad_simulator.register_callback(self.on_image_callback)
            self._ad_simulator.register_status_callback(self.on_status_callback)

    def doInit(self, mode):
        del mode
        self.update_arraydesc()
        self._image_array = np.zeros(self.arraydesc.shape, dtype=self.arraydesc.dtype)
        self._setROParam("curarray", self._image_array.copy())

    def _initialize_ad_simulator(self):
        self._ad_simulator._sizex = int(self.sizex)
        self._ad_simulator._sizey = int(self.sizey)
        self._ad_simulator._startx = int(self.startx)
        self._ad_simulator._starty = int(self.starty)
        self._ad_simulator._acquiretime = self.acquiretime
        self._ad_simulator._acquireperiod = self.acquireperiod
        self._ad_simulator._num_images = int(self.numimages)
        self._ad_simulator._image_mode = self.imagemode
        self._ad_simulator._binning = self.binning

    def _update_status(self, new_status, message):
        self._setROParam("curstatus", (new_status, message))

    def on_status_callback(self):
        new_status, message = self._ad_simulator._status
        self._update_status(new_status, message)
        self._setROParam("curvalue", self._ad_simulator._image_counter)

    def on_image_callback(self):
        new_status, message = self._ad_simulator._status
        self._update_status(new_status, message)
        self.log.info("Image acquired")
        if time.monotonic() >= self._last_update + self._plot_update_delay:
            createThread(f"get_image_{time.time_ns()}", self.get_image)

    def _refresh_image(self, *, image_count, emit_live, completed):
        dataarray = super()._refresh_image(
            image_count=image_count,
            emit_live=emit_live,
            completed=completed,
        )
        self._setROParam(
            "curarray",
            np.array(dataarray, copy=True, order="C"),
        )
        self._setROParam("curvalue", int(image_count))
        return dataarray

    def _epics_status_tuple(self):
        return self.curstatus

    def _epics_alarm_status(self):
        current_status = self._epics_status_tuple()[0]
        if current_status == status.UNKNOWN:
            return 17
        if current_status >= status.ERROR:
            return 9
        return 0

    def _epics_alarm_severity(self):
        current_status = self._epics_status_tuple()[0]
        if current_status == status.UNKNOWN:
            return 3
        if current_status == status.WARN:
            return 1
        if current_status >= status.ERROR:
            return 2
        return 0

    def _acquire_status(self):
        current_status, message = self._epics_status_tuple()
        if current_status == status.BUSY:
            return message or "Acquiring"
        if current_status == status.OK:
            return message or "Done"
        return message or "Error"

    def _get_pv(self, pvparam, as_string=False):
        del as_string
        if pvparam == "max_size_x":
            return self._ad_simulator._max_sizex
        if pvparam == "max_size_y":
            return self._ad_simulator._max_sizey
        if pvparam == "data_type":
            return "UInt16"
        if pvparam == "readpv":
            if session.sessiontype == POLLER:
                return self.curvalue
            return self._ad_simulator._image_counter
        if pvparam == "detector_state.STAT":
            return self._epics_alarm_status()
        if pvparam == "detector_state.SEVR":
            return self._epics_alarm_severity()
        if pvparam == "acquire_status":
            return self._acquire_status()
        if pvparam == "image_pv":
            if session.sessiontype == POLLER:
                return self.curarray
            return self._ad_simulator._image
        raise KeyError(pvparam)

    def _put_pv(self, pvparam, value, wait=False):
        del wait
        if pvparam != "acquire":
            raise KeyError(pvparam)
        if value:
            self._ad_simulator.acquire()
        else:
            self._ad_simulator.stop()

    def update_arraydesc(self):
        shape = (int(self.sizey), int(self.sizex))
        binning_factor = int(self.binning[0])
        shape = (shape[0] // binning_factor, shape[1] // binning_factor)
        self._plot_update_delay = (shape[0] * shape[1]) / 2097152.0
        self.arraydesc = ArrayDesc(self.name, shape=shape, dtype=np.uint16)

    def doStart(self, **preset):
        del preset
        num_images = self._requested_image_count()
        if num_images == 0:
            return
        if not num_images or num_images < 0:
            self._ad_simulator._image_mode = "continuous"
        elif num_images == 1:
            self._ad_simulator._image_mode = "single"
            self._ad_simulator._num_images = 1
        else:
            self._ad_simulator._image_mode = "multiple"
            self._ad_simulator._num_images = int(num_images)
        super().doStart()

    def _limit_size(self, value, max_value):
        if value > max_value:
            value = max_value
        return int(value)

    def _limit_start(self, value):
        if value < 0:
            value = 0
        return int(value)

    def doReadSizex(self):
        return self._ad_simulator._sizex

    def doWriteSizex(self, value):
        self._ad_simulator._sizex = self._limit_size(
            value, self._ad_simulator._max_sizex
        )

    def doReadSizey(self):
        return self._ad_simulator._sizey

    def doWriteSizey(self, value):
        self._ad_simulator._sizey = self._limit_size(
            value, self._ad_simulator._max_sizey
        )

    def doReadStartx(self):
        return self._ad_simulator._startx

    def doWriteStartx(self, value):
        self._ad_simulator._startx = self._limit_start(value)

    def doReadStarty(self):
        return self._ad_simulator._starty

    def doWriteStarty(self, value):
        self._ad_simulator._starty = self._limit_start(value)

    def doReadAcquiretime(self):
        return self._ad_simulator._acquiretime

    def doWriteAcquiretime(self, value):
        self._ad_simulator._acquiretime = value

    def doReadAcquireperiod(self):
        return self._ad_simulator._acquireperiod

    def doWriteAcquireperiod(self, value):
        self._ad_simulator._acquireperiod = value

    def doReadNumimages(self):
        return self._ad_simulator._num_images

    def doWriteNumimages(self, value):
        self._ad_simulator._num_images = int(value)

    def doWriteImagemode(self, value):
        self._ad_simulator._image_mode = value

    def doReadImagemode(self):
        return self._ad_simulator._image_mode

    def doReadBinning(self):
        return self._ad_simulator._binning

    def doWriteBinning(self, value):
        self._ad_simulator._binning = value

    def get_topic_and_source(self):
        return "some_topic", "some_source"
