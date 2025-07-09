import threading
import time
from enum import Enum

import numpy
import numpy as np

from nicos import session
from nicos.core import (
    LIVE,
    POLLER,
    SIMULATION,
    ArrayDesc,
    CacheError,
    Measurable,
    Override,
    Param,
    Value,
    floatrange,
    multiStatus,
    oneof,
    status,
    tupleof,
    usermethod,
)
from nicos.devices.generic import Detector, ImageChannelMixin, ManualSwitch
from nicos.utils import byteBuffer, createThread

binning_factor_map = {
    0: "1x1",
    1: "2x2",
    2: "4x4",
}

PROJECTION, FLATFIELD, DARKFIELD, INVALID = 0, 1, 2, 3


class ImageMode(Enum):
    SINGLE = 0
    MULTIPLE = 1
    CONTINUOUS = 2


class ImageType(ManualSwitch):
    """
    Class that contains the image type for a tomography experiment using the
    epics AreaDetector class.
    """

    parameter_overrides = {
        "fmtstr": Override(default="%d"),
        "states": Override(
            mandatory=False, default=list(range(PROJECTION, INVALID + 1))
        ),
        "maxage": Override(default=0),
        "pollinterval": Override(default=None, userparam=False, settable=False),
    }

    hardware_access = False

    _image_key_to_image_type = {
        PROJECTION: "Projection",
        FLATFIELD: "Flat field",
        DARKFIELD: "Dark field",
        INVALID: "Invalid",
    }

    def doStatus(self, maxage=0):
        if self.target == INVALID:
            return status.WARN, "State is invalid for a tomography experiment."
        return status.OK, self._image_key_to_image_type[self.target]

    def doStart(self, target):
        ManualSwitch.doStart(self, target)
        if self._mode != SIMULATION:
            if not self._cache:
                raise CacheError(
                    self,
                    "Detector requires a running cache for "
                    "full functionality. Please check its status.",
                )
            curr_time = time.time()
            self._cache.put(self._name, "value", target, curr_time)
            self._cache.put(self._name, "status", self.doStatus(), curr_time)

    @usermethod
    def set_to_projection(self):
        """Set the image key to projection"""
        self.move(PROJECTION)

    @usermethod
    def set_to_flat_field(self):
        """Set the image key to flat field"""
        self.move(FLATFIELD)

    @usermethod
    def set_to_dark_field(self):
        """Set the image key to dark field"""
        self.move(DARKFIELD)

    @usermethod
    def set_to_invalid(self):
        """Set the image key to invalid"""
        self.move(INVALID)


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
        self._running_flag.clear()
        self._run_thread.start()
        self._status_thread.start()
        self._status = status.OK, "Done"
        self._image = np.zeros((self._max_sizey, self._max_sizex))

    def register_callback(self, callback):
        self._callback = callback

    def register_status_callback(self, callback):
        self._status_callback = callback

    def _update_status(self):
        while True:
            if self._running_flag.is_set():
                self._status = status.BUSY, "Acquiring"
            else:
                self._status = status.OK, "Done"
            if self._status_callback is not None:
                self._status_callback()
            time.sleep(1)

    def acquire(self):
        self._running_flag.set()
        self._image_counter = 0

    def stop(self):
        self._running_flag.clear()

    def _run(self):
        while True:
            if self._running_flag.is_set():
                self._status = status.BUSY, "Acquiring"
                self._status_callback()
                time.sleep(self._acquireperiod)
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


class AreaDetector(ImageChannelMixin, Measurable):
    """
    Device that controls and acquires data from an area detector.
    """

    _hardware_access = False

    parameters = {
        "iscontroller": Param(
            "If this channel is an active controller",
            type=bool,
            settable=True,
            default=True,
        ),
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
        "acquiretime": Param("Exposure time ", settable=True, volatile=False),
        "acquireperiod": Param(
            "Time between exposure starts.", settable=True, volatile=False
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

    _image_array = numpy.zeros((10, 10))
    _detector_collector_name = ""
    _last_update = 0
    _plot_update_delay = 2.0

    def doPreinit(self, mode):
        if mode == SIMULATION:
            return
        self._image_processing_lock = threading.Lock()

        self._ad_simulator = FakeAreaDetector()
        self._initilize_ad_simulator()
        if session.sessiontype != POLLER:
            self._ad_simulator.register_callback(self.on_image_callback)
            self._ad_simulator.register_status_callback(self.on_status_callback)

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
        self._update_status(status.BUSY, "Preparing")
        self._update_status(status.OK, "")
        self.arraydesc = self.arrayInfo()

    def _update_status(self, new_status, message):
        self._cache.put(self._name, "status", self.curstatus, time.time())
        self._setROParam("curstatus", (new_status, message))

    def on_status_callback(self):
        status, message = self._ad_simulator._status
        self._update_status(status, message)
        self._cache.put(
            self._name, "value", self._ad_simulator._image_counter, time.time()
        )

    def valueInfo(self):
        return (Value(self.name, fmtstr="%d"),)

    def arrayInfo(self):
        self.update_arraydesc()
        return self.arraydesc

    def update_arraydesc(self):
        shape = self.sizey, self.sizex
        binning_factor = int(self.binning[0])
        shape = (shape[0] // binning_factor, shape[1] // binning_factor)
        self._plot_update_delay = (shape[0] * shape[1]) / 2097152.0
        data_type = np.uint16
        self.arraydesc = ArrayDesc(self.name, shape=shape, dtype=data_type)

    def doIsCompleted(self):
        _thread = createThread(f"get_image_{time.time_ns()}", self.get_image)

    def on_image_callback(self):
        status, message = self._ad_simulator._status
        self._update_status(status, message)
        self.log.info("Image acquired")
        # if time.monotonic() - self._last_update > self._plot_update_delay:
        _thread = createThread(f"get_image_{time.time_ns()}", self.get_image)

    def get_image(self):
        dataarray = self._ad_simulator._image
        shape = self.arrayInfo().shape
        dataarray = dataarray.reshape(shape)
        self.putResult(LIVE, dataarray, time.time())
        self._last_update = time.monotonic()

    def putResult(self, quality, data, timestamp):
        self._image_array = data
        databuffer = [byteBuffer(numpy.ascontiguousarray(data))]
        datadesc = [
            dict(
                dtype=data.dtype.str,
                shape=data.shape,
                labels={
                    "x": {"define": "classic"},
                    "y": {"define": "classic"},
                },
                plotcount=1,
            )
        ]
        if databuffer:
            parameters = dict(
                uid=0,
                time=timestamp,
                det=self._detector_collector_name,
                tag=LIVE,
                datadescs=datadesc,
            )
            labelbuffers = []
            with self._image_processing_lock:
                session.updateLiveData(parameters, databuffer, labelbuffers)

    def doSetPreset(self, **preset):
        if not preset:
            # keep old settings
            return
        self._lastpreset = preset.copy()

    def doStatus(self, maxage=0):
        severity, state = self.curstatus
        return severity, state

    def _limit_size(self, value, max_value):
        if value > max_value:
            value = max_value
        return int(value)

    def _limit_start(self, value):
        if value < 0:
            value = 0
        return int(value)

    def doStart(self, **preset):
        num_images = self._lastpreset.get("n", None)

        if num_images == 0:
            return
        elif not num_images or num_images < 0:
            self.imagemode = "continuous"
        elif num_images == 1:
            self.imagemode = "single"
        elif num_images > 1:
            self.imagemode = "multiple"
            self.numimages = num_images

        self.doAcquire()

    def doAcquire(self):
        self._ad_simulator.acquire()

    def doFinish(self):
        self.doStop()

    def doStop(self):
        self._ad_simulator.stop()

    def doRead(self, maxage=0):
        return self._ad_simulator._image_counter

    def doReadArray(self, quality):
        return self._image_array

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

    def get_topic_and_source(self):
        return "some_topic", "some_source"


class AreaDetectorCollector(Detector):
    """
    A device class that collects the area detectors present in the instrument
    setup.
    """

    parameter_overrides = {
        "unit": Override(default="images", settable=False, mandatory=False),
        "fmtstr": Override(default="%d"),
        "liveinterval": Override(type=floatrange(0.5), default=1, userparam=True),
        "pollinterval": Override(default=1, userparam=True, settable=False),
        "statustopic": Override(default="", mandatory=False),
    }

    _presetkeys = set()
    _hardware_access = False

    def doPreinit(self, mode):
        for image_channel in self._attached_images:
            image_channel._detector_collector_name = self.name
            self._presetkeys.add(image_channel.name)
        self._channels = self._attached_images
        self._collectControllers()

    def _collectControllers(self):
        self._controlchannels, self._followchannels = self._attached_images, []

    def get_array_size(self, topic, source):
        for area_detector in self._attached_images:
            if (topic, source) == area_detector.get_topic_and_source():
                return area_detector.arrayInfo().shape
        self.log.error(
            "No array size was found for area detector with topic %s and source %s.",
            topic,
            source,
        )
        return []

    def doSetPreset(self, **preset):
        if not preset:
            # keep old settings
            return

        for controller in self._controlchannels:
            sub_preset = preset.get(controller.name, None)
            if sub_preset:
                controller.doSetPreset(**{"n": sub_preset})

        self._lastpreset = preset.copy()

    def doStatus(self, maxage=0):
        return multiStatus(self._attached_images, maxage)

    def doRead(self, maxage=0):
        return []

    def doReadArrays(self, quality):
        return [image.readArray(quality) for image in self._attached_images]

    def doReset(self):
        pass

    def duringMeasureHook(self, elapsed):
        if self.liveinterval is not None:
            if elapsed > self._last_live + self.liveinterval:
                self._last_live = elapsed
                return LIVE
        return None

    def arrayInfo(self):
        return tuple(ch.arrayInfo() for ch in self._attached_images)

    def doTime(self, preset):
        return 0
