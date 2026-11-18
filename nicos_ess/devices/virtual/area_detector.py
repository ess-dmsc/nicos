import threading
import time
from enum import Enum

import numpy as np

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    ArrayDesc,
    Override,
    Param,
    Value,
    oneof,
    status,
    tupleof,
)
from nicos.devices.generic import ActiveChannel, ImageChannelMixin

binning_factor_map = {
    0: "1x1",
    1: "2x2",
    2: "4x4",
}


class ImageMode(Enum):
    SINGLE = 0
    MULTIPLE = 1
    CONTINUOUS = 2


class FakeAreaDetector:
    def __init__(self):
        self._image_modes = ["single", "multiple", "continuous"]
        self._binning_factors = ["1x1", "2x2", "4x4"]
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
        self._closed = threading.Event()
        self._run_thread.start()
        self._status_thread.start()
        self._status = status.OK, "Done"
        self._image = np.zeros((self._max_sizey, self._max_sizex))

    def register_callback(self, callback):
        self._callback = callback

    def register_status_callback(self, callback):
        self._status_callback = callback

    def _update_status(self):
        while not self._closed.is_set():
            if self._running_flag.is_set():
                self._status = status.BUSY, "Acquiring"
            else:
                self._status = status.OK, "Done"
            if self._status_callback is not None:
                self._status_callback()
            self._closed.wait(1)

    def acquire(self):
        self._running_flag.set()
        self._image_counter = 0

    def stop(self):
        self._running_flag.clear()

    def close(self):
        self._running_flag.clear()
        self._closed.set()
        self._run_thread.join()
        self._status_thread.join()

    def _run(self):
        while not self._closed.is_set():
            if self._running_flag.is_set():
                self._status = status.BUSY, "Acquiring"
                self._status_callback()
                if self._closed.wait(self._acquireperiod):
                    return
                self._gen_image()
                self._status_callback()

                if self._image_mode == "single":
                    self._running_flag.clear()
                    self._status_callback()
                elif self._image_mode == "multiple":
                    if self._image_counter >= self._num_images:
                        self._running_flag.clear()
                        self._status_callback()
            else:
                self._status = status.OK, "Done"
                time.sleep(0.01)

    def _gen_image(self):
        self._status = status.BUSY, "Acquiring"
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

        self._image = image.flatten()
        self._image_counter += 1
        if self._callback:
            self._callback()


class AreaDetector(ImageChannelMixin, ActiveChannel):
    """A simulated camera as a NICOS image channel.

    With a preset such as ``count(virtual_camera=3)`` the camera stops after
    that many images. Without a preset it acquires until the detector
    finishes it.
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
        "sizex": Param("Image X size.", settable=True, volatile=False, type=int),
        "sizey": Param("Image Y size.", settable=True, volatile=False, type=int),
        "startx": Param(
            "Image X start index.", settable=True, volatile=False, type=int
        ),
        "starty": Param(
            "Image Y start index.", settable=True, volatile=False, type=int
        ),
        "acquiretime": Param(
            "Exposure time.", unit="s", default=0.1, settable=True, volatile=False
        ),
        "acquireperiod": Param(
            "Time between exposure starts.",
            unit="s",
            default=1.0,
            settable=True,
            volatile=False,
        ),
        "numimages": Param(
            "Number of images to take (only in imageMode=multiple).",
            settable=True,
            volatile=False,
            type=int,
        ),
        "curstatus": Param(
            "Store the current device status",
            internal=True,
            type=tupleof(int, str),
            settable=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(default="images", mandatory=False),
    }

    def doPreinit(self, mode):
        self.arraydesc = ArrayDesc(self.name, shape=(1, 1), dtype=np.uint16)
        if mode == SIMULATION:
            return
        self._ad_simulator = FakeAreaDetector()
        self._initilize_ad_simulator()
        if session.sessiontype != POLLER:
            self._ad_simulator.register_status_callback(self.on_status_callback)

    def doShutdown(self):
        if hasattr(self, "_ad_simulator"):
            self._ad_simulator.close()

    def _initilize_ad_simulator(self):
        self._ad_simulator._sizex = int(self.sizex)
        self._ad_simulator._sizey = int(self.sizey)
        self._ad_simulator._startx = int(self.startx)
        self._ad_simulator._starty = int(self.starty)
        self._ad_simulator._acquiretime = self.acquiretime
        self._ad_simulator._acquireperiod = self.acquireperiod
        self._ad_simulator._num_images = int(self.numimages)
        self._ad_simulator._image_mode = self.imagemode
        self._ad_simulator._binning = self.binning

    def doPrepare(self):
        self.update_arraydesc()

    def _update_status(self, new_status, message):
        self._setROParam("curstatus", (new_status, message))
        self._cache.put(self._name, "status", self.curstatus, time.time())

    def on_status_callback(self):
        self._update_status(*self.doStatus())
        self._cache.put(
            self._name, "value", [self._ad_simulator._image_counter], time.time()
        )

    def valueInfo(self):
        return (Value(self.name, unit=self.unit, type="counter", fmtstr="%d"),)

    def arrayInfo(self):
        self.update_arraydesc()
        return (self.arraydesc,)

    def update_arraydesc(self):
        binning_factor = int(self.binning[0])
        shape = (self.sizey // binning_factor, self.sizex // binning_factor)
        self.arraydesc = ArrayDesc(self.name, shape=shape, dtype=np.uint16)

    def doStatus(self, maxage=0):
        # The poller has its own simulator that never acquires, so it shows
        # the status that the daemon writes.
        if session.sessiontype == POLLER:
            return self.curstatus
        if self._ad_simulator._running_flag.is_set():
            return status.BUSY, "Acquiring"
        return status.OK, ""

    def _limit_size(self, value, max_value):
        if value > max_value:
            value = max_value
        return int(value)

    def _limit_start(self, value):
        if value < 0:
            value = 0
        return int(value)

    def doStart(self):
        if not self.iscontroller or not self.preselection:
            self.imagemode = "continuous"
        elif self.preselection == 1:
            self.imagemode = "single"
        else:
            self.imagemode = "multiple"
            self.numimages = self.preselection
        self._ad_simulator.acquire()
        self._update_status(status.BUSY, "Acquiring")

    def doFinish(self):
        self.doStop()

    def doStop(self):
        self._ad_simulator.stop()

    def doRead(self, maxage=0):
        return [self._ad_simulator._image_counter]

    def doReadArray(self, quality):
        # The simulator keeps the last image of the previous count until the
        # first image of this count is taken.
        if not self._ad_simulator._image_counter:
            return None
        image = self._ad_simulator._image
        self.update_arraydesc()
        if image.size != int(np.prod(self.arraydesc.shape)):
            return None
        return image.reshape(self.arraydesc.shape).astype(self.arraydesc.dtype)

    def doTime(self, preset):
        if not self.iscontroller or not self.preselection:
            return 0
        return self.preselection * self.acquireperiod

    def doSimulate(self, preset):
        return [self.preselection if self.iscontroller else 0]

    def doReadSizex(self):
        return self._ad_simulator._sizex

    def doWriteSizex(self, value):
        self._ad_simulator._sizex = int(
            self._limit_size(value, self._ad_simulator._max_sizex)
        )

    def doReadSizey(self):
        return self._ad_simulator._sizey

    def doWriteSizey(self, value):
        self._ad_simulator._sizey = int(
            self._limit_size(value, self._ad_simulator._max_sizey)
        )

    def doReadStartx(self):
        return self._ad_simulator._startx

    def doWriteStartx(self, value):
        self._ad_simulator._startx = int(self._limit_start(value))

    def doReadStarty(self):
        return self._ad_simulator._starty

    def doWriteStarty(self, value):
        self._ad_simulator._starty = int(self._limit_start(value))

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
