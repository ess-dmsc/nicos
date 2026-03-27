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
    InvalidValueError,
    Measurable,
    Override,
    Param,
    Value,
    floatrange,
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
                    self._status = status.OK, "Done"
                    self._status_callback()
                elif self._image_mode == "multiple":
                    if self._image_counter >= self._num_images:
                        self._running_flag.clear()
                        self._status = status.OK, "Done"
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
    _cached_image_count = 0
    _completed_image_count = 0

    def doPreinit(self, mode):
        if mode == SIMULATION:
            return
        self._image_processing_lock = threading.RLock()

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
        self._begin_acquisition_cycle()
        self._update_status(status.OK, "")
        self.arraydesc = self.arrayInfo()[0]

    def _begin_acquisition_cycle(self):
        self._cached_image_count = 0
        self._completed_image_count = 0
        self._last_update = 0

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
        return tuple([self.arraydesc])

    def update_arraydesc(self):
        shape = self.sizey, self.sizex
        binning_factor = int(self.binning[0])
        shape = (shape[0] // binning_factor, shape[1] // binning_factor)
        self._plot_update_delay = (shape[0] * shape[1]) / 2097152.0
        data_type = np.uint16
        self.arraydesc = ArrayDesc(self.name, shape=shape, dtype=data_type)

    def on_image_callback(self):
        status, message = self._ad_simulator._status
        self._update_status(status, message)
        self.log.info("Image acquired")
        # Mirror the real detector behavior: sample sparse livedata updates
        # rather than trying to publish every generated frame.
        if time.monotonic() - self._last_update > self._plot_update_delay:
            _thread = createThread(f"get_image_{time.time_ns()}", self.get_image)

    def get_image(self):
        with self._image_processing_lock:
            self._refresh_image(
                image_count=self.read(0)[0],
                emit_live=True,
                completed=self.status(0)[0] not in self.busystates,
            )

    def _refresh_image(self, *, image_count, emit_live, completed):
        dataarray = self._ad_simulator._image
        shape = self.arrayInfo()[0].shape
        dataarray = dataarray.reshape(shape)
        self._image_array = dataarray
        self._cached_image_count = image_count
        if completed:
            self._completed_image_count = image_count
        self._last_update = time.monotonic()
        if emit_live:
            self.putResult(LIVE, dataarray, time.time())
        return dataarray

    def sync_cached_image(
        self, required_count, *, emit_live=True, after_completion=False
    ):
        """Ensure the cached image has caught up to at least `required_count`.

        Like the EPICS implementation, this samples the simulator's latest
        frame instead of replaying every intermediate one. The cached image is
        considered final only once acquisition is no longer busy.
        """
        if required_count <= 0:
            return True
        with self._image_processing_lock:
            synced_count = (
                self._completed_image_count
                if after_completion
                else self._cached_image_count
            )
            if synced_count >= required_count:
                return True
            captured_count = self.read(0)[0]
            completed = self.status(0)[0] not in self.busystates
            self._refresh_image(
                image_count=captured_count,
                emit_live=emit_live,
                completed=completed,
            )
            synced_count = (
                self._completed_image_count
                if after_completion
                else self._cached_image_count
            )
            return synced_count >= required_count

    def putResult(self, quality, data, timestamp):
        del quality
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

    def presetInfo(self):
        return ("n",)

    def doSetPreset(self, **preset):
        if not preset:
            preset = self._lastpreset or {}
        if "n" in preset:
            self._lastpreset = {"n": int(preset["n"])}

    def setChannelPreset(self, name, value):
        if name not in {"n", self.name}:
            raise InvalidValueError(
                self,
                f"unrecognised preset {name}, should be one of n or {self.name}",
            )
        self.iscontroller = True
        self.doSetPreset(n=value)

    def presetReached(self, name, value, maxage):
        del name
        current_count = self.read(maxage)[0]
        if current_count < value:
            return False
        st = self.status(0)
        if st[0] in self.errorstates:
            raise self.errorstates[st[0]](self, st[1])
        if st[0] in self.busystates:
            # Reaching the count target alone is not enough; while still busy
            # we may update sparse livedata, but the final image is not yet
            # guaranteed to be ready.
            self.sync_cached_image(current_count, after_completion=False)
            return False
        # Once the simulator reports done, force the cached image to catch up
        # before NICOS sees the preset as completed.
        return self.sync_cached_image(current_count, after_completion=True)

    def doIsCompleted(self):
        st = self.status(0)
        if st[0] in self.errorstates:
            raise self.errorstates[st[0]](self, st[1])
        current_count = self.read(0)[0]
        target = (self._lastpreset or {}).get("n")
        if target is not None:
            if current_count < target:
                return False
        if st[0] in self.busystates:
            if current_count > self._cached_image_count:
                # Keep sparse livedata reasonably fresh during acquisition
                # without changing the rule that completion waits for Done.
                self.sync_cached_image(current_count, after_completion=False)
            return False
        # Report completion only after the final frame has been synchronized
        # into the cached image buffer.
        return self.sync_cached_image(current_count, after_completion=True)

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
        num_images = (self._lastpreset or {}).get("n", None)
        if num_images == 0:
            return
        elif not num_images or num_images < 0:
            self.imagemode = "continuous"
        elif num_images == 1:
            self.imagemode = "single"
        elif num_images > 1:
            self.imagemode = "multiple"
            self.numimages = num_images
        self._begin_acquisition_cycle()
        self._update_status(status.BUSY, "Acquiring")
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

    _hardware_access = False
    _measurement_started = False

    def doPreinit(self, mode):
        for image_channel in self._attached_images:
            image_channel._detector_collector_name = self.name
        super().doPreinit(mode)

    def doPrepare(self):
        self._measurement_started = False
        Detector.doPrepare(self)

    def doStart(self):
        self._measurement_started = True
        Detector.doStart(self)

    def doFinish(self):
        try:
            Detector.doFinish(self)
        finally:
            self._measurement_started = False

    def doStop(self):
        try:
            Detector.doStop(self)
        finally:
            self._measurement_started = False

    def _presetiter(self):
        for image_channel in self._attached_images:
            yield (image_channel.name, image_channel, "counts")
        yield ("live", None, "other")

    def get_array_size(self, topic, source):
        for area_detector in self._attached_images:
            if (topic, source) == area_detector.get_topic_and_source():
                return area_detector.arrayInfo()[0].shape
        self.log.error(
            "No array size was found for area detector with topic %s and source %s.",
            topic,
            source,
        )
        return []

    def doSetPreset(self, **preset):
        filtered = {
            name: value
            for name, value in preset.items()
            if name == "info" or name in self._presetkeys
        }
        Detector.doSetPreset(self, **filtered)

    def doRead(self, maxage=0):
        return []

    def valueInfo(self):
        return ()

    def doIsCompleted(self):
        any_busy = False
        for ch in self._channels:
            st = ch.status(0)
            if st[0] in ch.errorstates:
                raise ch.errorstates[st[0]](ch, st[1])
            if st[0] in ch.busystates:
                any_busy = True

        if not self._measurement_started:
            return not any_busy

        controller_reached = False
        for controller in self._controlchannels:
            for name, value in self._channel_presets.get(controller, ()):
                if controller.presetReached(name, value, 0):
                    controller_reached = True
                    break
            if controller_reached:
                break
        if controller_reached:
            if not any_busy:
                # Match the real collector: before FINAL readout, make sure the
                # attached images have performed their post-completion sync.
                for image in self._attached_images:
                    image.sync_cached_image(image.read(0)[0], after_completion=True)
            return True
        if any_busy:
            return False
        # If nothing is busy anymore, still perform one final sync pass so
        # readResults(FINAL) sees the last completed frame.
        for image in self._attached_images:
            image.sync_cached_image(image.read(0)[0], after_completion=True)
        return True

    def doReset(self):
        pass

    def arrayInfo(self):
        return tuple(ch.arrayInfo()[0] for ch in self._attached_images)
