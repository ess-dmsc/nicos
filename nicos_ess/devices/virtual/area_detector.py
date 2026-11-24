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
    Value,
    oneof,
    status,
    tupleof,
)
from nicos.devices.generic import ActiveChannel, ImageChannelMixin

SENSOR_PIXELS = 1024


def sensor_slice(start, size, binning):
    """Return the sensor pixels along one axis that a region covers.

    Like an ADCore driver, the region is cut to the sensor and to whole bins.
    """
    start = min(max(start, 0), SENSOR_PIXELS - binning)
    size = min(max(size, binning), SENSOR_PIXELS - start)
    return slice(start, start + size - size % binning)


class FakeAreaDetector:
    """A sensor that takes images in a thread with the settings of *camera*."""

    def __init__(self, camera, on_change):
        self._camera = camera
        self._on_change = on_change
        self.image = None
        self.image_counter = 0
        self.acquiring = threading.Event()
        self._run_number = 0
        self._closed = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def acquire(self):
        self.image_counter = 0
        self._run_number += 1
        self.acquiring.set()

    def close(self):
        self.acquiring.clear()
        self._closed.set()
        self._thread.join()

    def _run(self):
        while not self._closed.is_set():
            if not self.acquiring.wait(0.01):
                continue
            run_number = self._run_number
            if self._closed.wait(self._camera.acquireperiod):
                continue
            image = self._take_image()
            # The image belongs to no run if the run was stopped or restarted
            # during the period or the exposure.
            if run_number != self._run_number or not self.acquiring.is_set():
                continue
            self.image = image
            self.image_counter += 1
            mode = self._camera.imagemode
            if mode == "single" or (
                mode == "multiple" and self.image_counter >= self._camera.numimages
            ):
                self.acquiring.clear()
            self._on_change()

    def _take_image(self):
        y, x = np.mgrid[:SENSOR_PIXELS, :SENSOR_PIXELS] / SENSOR_PIXELS
        image = np.exp(-32 * (x - 0.5) ** 2 - 8 * (y - 0.6) ** 2)
        image += np.abs(np.random.normal(0, 0.1, image.shape))
        image *= 100 * self._camera.acquiretime * np.random.uniform(0.8, 1.2)
        binning, rows, columns = self._camera.region()
        image = image[rows, columns]
        height, width = image.shape
        return image.reshape(
            height // binning, binning, width // binning, binning
        ).mean(axis=(1, 3))


class AreaDetector(ImageChannelMixin, ActiveChannel):
    """A simulated camera as a NICOS image channel.

    With a preset such as ``count(virtual_camera=3)`` the camera stops after
    that many images. Without a preset it acquires until the detector
    finishes it. Like the setpoints of an ADCore driver, the region parameters
    keep the requested values, and the frames and arrayInfo show the region
    cut to the sensor and to whole bins.
    """

    parameters = {
        "imagemode": Param(
            "Mode to acquire images.",
            type=oneof("single", "multiple", "continuous"),
            settable=True,
            default="continuous",
        ),
        "binning": Param(
            "Binning factor",
            type=oneof("1x1", "2x2", "4x4"),
            settable=True,
            default="1x1",
        ),
        "sizex": Param("Image X size.", type=int, settable=True, default=SENSOR_PIXELS),
        "sizey": Param("Image Y size.", type=int, settable=True, default=SENSOR_PIXELS),
        "startx": Param("Image X start index.", type=int, settable=True),
        "starty": Param("Image Y start index.", type=int, settable=True),
        "acquiretime": Param("Exposure time.", unit="s", default=0.1, settable=True),
        "acquireperiod": Param(
            "Time between exposure starts.", unit="s", default=1.0, settable=True
        ),
        "numimages": Param(
            "Number of images to take (only in imageMode=multiple).",
            type=int,
            settable=True,
            default=1,
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
        if mode != SIMULATION:
            self._ad_simulator = FakeAreaDetector(self, self.on_status_callback)

    def doShutdown(self):
        if hasattr(self, "_ad_simulator"):
            self._ad_simulator.close()

    def doPrepare(self):
        self.update_arraydesc()

    def _update_status(self, new_status, message):
        self._setROParam("curstatus", (new_status, message))
        self._cache.put(self._name, "status", self.curstatus, time.time())

    def on_status_callback(self):
        self._update_status(*self.doStatus())
        self._cache.put(
            self._name, "value", [self._ad_simulator.image_counter], time.time()
        )

    def valueInfo(self):
        return (Value(self.name, unit=self.unit, type="counter", fmtstr="%d"),)

    def arrayInfo(self):
        self.update_arraydesc()
        return (self.arraydesc,)

    def region(self):
        """Return the binning and the sensor rows and columns of a frame."""
        binning = int(self.binning[0])
        rows = sensor_slice(self.starty, self.sizey, binning)
        columns = sensor_slice(self.startx, self.sizex, binning)
        return binning, rows, columns

    def update_arraydesc(self):
        binning, rows, columns = self.region()
        shape = (
            (rows.stop - rows.start) // binning,
            (columns.stop - columns.start) // binning,
        )
        self.arraydesc = ArrayDesc(self.name, shape=shape, dtype=np.uint16)

    def doStatus(self, maxage=0):
        # The poller has its own simulator that never acquires, so it shows
        # the status that the daemon writes.
        if session.sessiontype == POLLER:
            return self.curstatus
        if self._ad_simulator.acquiring.is_set():
            return status.BUSY, "Acquiring"
        return status.OK, ""

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
        self._ad_simulator.acquiring.clear()
        self.on_status_callback()

    def doRead(self, maxage=0):
        return [self._ad_simulator.image_counter]

    def doReadArray(self, quality):
        # The simulator keeps the last image of the previous count until the
        # first image of this count is taken.
        if not self._ad_simulator.image_counter:
            return None
        image = self._ad_simulator.image.astype(np.uint16)
        self.arraydesc = ArrayDesc(self.name, shape=image.shape, dtype=image.dtype)
        return image

    def doTime(self, preset):
        if not self.iscontroller or not self.preselection:
            return 0
        return self.preselection * self.acquireperiod

    def doSimulate(self, preset):
        return [self.preselection if self.iscontroller else 0]
