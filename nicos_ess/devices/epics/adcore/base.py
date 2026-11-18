"""The generic EPICS areaDetector image channel.

`AreaDetector` is an image channel for a stock ``nicos.devices.generic.Detector``.
``ArrayData`` is only read on demand and is never monitored or cached. The
``uniqueId`` of a frame is checked so that every frame handed out belongs to
the running acquisition.
"""

import dataclasses
import threading
import time

import numpy

from nicos import session
from nicos.core import (
    FINAL,
    LIVE,
    POLLER,
    SIMULATION,
    ArrayDesc,
    CommunicationError,
    HardwareError,
    Override,
    Param,
    Value,
    floatrange,
    pvname,
    status,
)
from nicos.devices.generic import ActiveChannel, ImageChannelMixin
from nicos_ess.devices.epics.pva.epics_common import (
    LOST_CONNECTION_STATUS,
    EpicsDeviceBase,
    EpicsEnumParam,
    command_channel,
    enum_status_channel,
    readback_channel,
    setpoint_channel,
    worst_status,
)
from nicos_ess.utilities.live_frame import LiveArrayDesc, default_dims

#: How many ``ArraySize<n>_RBV`` records an NDArray plugin publishes.
MAX_DIMENSIONS = 3

# These are the ImageMode choices in ADBase.template.
SINGLE, MULTIPLE, CONTINUOUS = range(3)

# The status that _compute_status gives the camera for each DetectorState_RBV
# choice. Aborted was requested, so it is not an error. _compute_status handles
# Error itself.
DETECTOR_STATE_STATUS = {
    "Idle": status.OK,
    "Waiting": status.OK,
    "Aborted": status.OK,
    "Acquire": status.BUSY,
    "Readout": status.BUSY,
    "Correct": status.BUSY,
    "Saving": status.BUSY,
    "Initializing": status.BUSY,
    "Aborting": status.BUSY,
    "Error": status.WARN,
    "Disconnected": status.ERROR,
}


def setting_channels(param, setpoint, readback, is_enum=False, cached=True):
    """Return the channels ``<param>_set`` and ``<param>_rbv`` for one setting.

    The readback is monitored under the cache key of the parameter. Pass
    *cached* False for a setting that is not a parameter or whose parameter
    reads a different record.
    """
    return {
        f"{param}_set": setpoint_channel(
            setpoint, cache_key=None, subscribe=False, is_enum=is_enum
        ),
        f"{param}_rbv": readback_channel(
            readback,
            cache_key=param if cached else None,
            subscribe=cached,
            is_enum=is_enum,
        ),
    }


def adcore_setting(param, record, is_enum=False, cached=True):
    """Return the setting channels for ADCore records like ``Record_RBV``."""
    return setting_channels(param, record, f"{record}_RBV", is_enum, cached)


def ess_setting(param, record, is_enum=False, cached=True):
    """Return the setting channels for ESS driver records like ``Record-RB``."""
    return setting_channels(param, f"{record}-S", f"{record}-RB", is_enum, cached)


def reader(channel):
    """Return a ``doRead<Param>`` method that reads *channel* from the IOC."""
    return lambda self: self._epics.get_channel_value(channel)


def setting_methods(param):
    """Return ``doRead<Param>`` and ``doWrite<Param>`` for a `setting_channels` pair."""
    return reader(f"{param}_rbv"), lambda self, value: self._put_setting(param, value)


def _image_channel(suffix, **kwargs):
    kwargs.setdefault("subscribe", False)
    return readback_channel(suffix, pv_prefix_attr="image_pv_root", **kwargs)


class AreaDetector(ImageChannelMixin, EpicsDeviceBase, ActiveChannel):
    """One ADCore camera as a NICOS image channel.

    With a preset such as ``count(camera=10)`` the IOC stops after exactly that
    many images. It uses ImageMode Multiple for this, or Single for one image.
    Without a preset, for example ``count(t=5)`` with a timer on the same
    detector, the camera acquires in Continuous mode until the detector
    finishes it.
    """

    parameters = {
        "pv_root": Param("PV root of the camera port", type=pvname, mandatory=True),
        "image_unit": Param(
            "Unit of the pixel values in the live views, for example 'ADU' for "
            "camera grey levels or 'counts' for counted hits. Empty if unknown",
            type=str,
            default="",
            userparam=False,
        ),
        "image_counts": Param(
            "Whether the pixel values are counted hits. The live views sum "
            "counted hits when they combine pixels and average grey levels",
            type=bool,
            default=False,
            userparam=False,
        ),
        "image_pv_root": Param(
            "PV root of the NDStdArrays plugin that the frames are read from",
            type=pvname,
            mandatory=True,
        ),
        "starttimeout": Param(
            "How long start() waits for the IOC to report Acquiring",
            type=floatrange(0),
            default=5.0,
            unit="s",
            settable=True,
        ),
        "finishtimeout": Param(
            "How long finish() waits for the acquisition to end and the "
            "image plugin to receive the last frame",
            type=floatrange(0),
            default=5.0,
            unit="s",
            settable=True,
        ),
        "imagemode": Param(
            "How many images one acquisition produces",
            type=EpicsEnumParam("imagemode_rbv"),
            settable=True,
            volatile=True,
            category="general",
        ),
        "numimages": Param(
            "Images per acquisition in the Multiple image mode",
            type=int,
            settable=True,
            volatile=True,
            category="general",
        ),
        "acquiretime": Param(
            "Exposure time of a single image",
            type=float,
            unit="s",
            settable=True,
            volatile=True,
            category="general",
        ),
        "acquireperiod": Param(
            "Time between the starts of two exposures",
            type=float,
            unit="s",
            settable=True,
            volatile=True,
            category="general",
        ),
        "numexposures": Param(
            "Exposures accumulated into one image",
            type=int,
            settable=True,
            volatile=True,
            category="general",
        ),
        "arrayrate": Param(
            "Rate at which the camera produces arrays",
            type=float,
            unit="Hz",
            volatile=True,
        ),
        "datatype": Param(
            "Element type the image plugin declares",
            type=str,
            volatile=True,
            category="general",
        ),
        "droppedarrays": Param(
            "Arrays the image plugin dropped", type=int, volatile=True
        ),
        "counting": Param(
            "Whether a count that NICOS started on the camera is running",
            type=bool,
            default=False,
            internal=True,
        ),
        "pausedimages": Param(
            "Images of the count taken before its last resume, which restarts "
            "NumImagesCounter",
            type=int,
            default=0,
            internal=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, volatile=True),
    }

    _default_pv_prefix_attr = "pv_root"
    _primary_channel = "num_images_counter"
    # Probe one channel per IOC. ArrayData is not used here because connecting
    # to it reads the whole frame.
    _connect_channels = ("num_images_counter", "image_ndims")

    _epics_channels = {
        "num_images_counter": readback_channel(
            "NumImagesCounter_RBV", cache_key="value", primary=True
        ),
        # The uniqueId of the last NDArray from the driver is read on demand.
        "array_counter": readback_channel(
            "ArrayCounter_RBV", cache_key=None, subscribe=False
        ),
        "acquire": command_channel("Acquire"),
        "acquire_busy": enum_status_channel("AcquireBusy", cache_key="acquire_busy"),
        "detector_state": enum_status_channel(
            "DetectorState_RBV", cache_key="detector_state"
        ),
        "status_message": readback_channel(
            "StatusMessage_RBV", cache_key="status_message", as_string=True
        ),
        "array_rate": readback_channel("ArrayRate_RBV", cache_key="arrayrate"),
        # The image plugin can run in another IOC. The frame and its description
        # are read on demand. DataType_RBV is monitored so a dead plugin is noticed.
        "image_data": _image_channel(
            "ArrayData", cache_key=None, connect_on_startup=False
        ),
        "image_unique_id": _image_channel("UniqueId_RBV", cache_key=None),
        "image_received": _image_channel("ArrayCounter_RBV", cache_key=None),
        "image_ndims": _image_channel("NDimensions_RBV"),
        **{
            f"image_dim{i}": _image_channel(f"ArraySize{i}_RBV")
            for i in range(MAX_DIMENSIONS)
        },
        "image_datatype": _image_channel(
            "DataType_RBV",
            cache_key="datatype",
            is_enum=True,
            affects_status=True,
            subscribe=True,
        ),
        "image_dropped": _image_channel(
            "DroppedArrays_RBV", cache_key="droppedarrays", subscribe=True
        ),
        **adcore_setting("imagemode", "ImageMode", is_enum=True),
        **adcore_setting("numimages", "NumImages"),
        **adcore_setting("acquiretime", "AcquireTime"),
        **adcore_setting("acquireperiod", "AcquirePeriod"),
        **adcore_setting("numexposures", "NumExposures"),
    }

    def doPreinit(self, mode):
        self.arraydesc = ArrayDesc(self.name, shape=(1, 1), dtype=numpy.uint16)
        # These hold ArrayCounter of the driver and the uniqueId and the array
        # count of the plugin at the last start, and they are kept after the run
        # for the final read.
        self._start_counter = None
        self._start_unique_id = None
        self._start_received = None
        self._live_sent_unique_id = None
        self._dropped_arrays = 0
        EpicsDeviceBase.doPreinit(self, mode)

    def _after_subscribe(self, mode):
        if mode == SIMULATION:
            return
        if session.sessiontype == POLLER:
            # The poller recomputes the status when a run starts or ends,
            # because an IOC error is an error only during a run. A
            # doUpdateCounting hook cannot do this, because Device.init calls
            # the hook before the counting parameter has a value.
            self._cache.addCallback(self, "counting", self._on_counting_change)
            self._subscriptions.append(("counting", self._on_counting_change))
        try:
            self._refresh_arraydesc()
        except (CommunicationError, TimeoutError) as err:
            # A dead image plugin must not prevent creating the device.
            self.log.warning("cannot read the array description yet: %s", err)

    def _on_channel_update(self, update):
        # Monitor updates write only the cache and not _params, and the getter
        # would read from the IOC on the monitor thread, so the last count is
        # kept here.
        if update.channel == "image_dropped":
            if update.value > self._dropped_arrays:
                self.log.warning("the image plugin has dropped %d arrays", update.value)
            self._dropped_arrays = update.value
        elif update.channel == "num_images_counter":
            update = dataclasses.replace(update, value=update.value + self.pausedimages)
        EpicsDeviceBase._on_channel_update(self, update)

    def _on_counting_change(self, key, counting, timestamp):
        self._refresh_status(timestamp)

    def arrayInfo(self):
        return (self.arraydesc,)

    def _array_desc(self, shape, dtype):
        return LiveArrayDesc(
            self.name,
            shape,
            dtype,
            default_dims(len(shape)),
            unit=self.image_unit,
            counts=self.image_counts,
            binned=self._binned(),
            meta={"exposure": self.acquiretime},
        )

    def _binned(self):
        """Return the sensor pixels per frame pixel along binned dims, like {"x": 2}."""
        return {}

    def _refresh_arraydesc(self):
        shape, dtype = self._describe()
        if shape is None:
            # A plugin that has not received a frame since its IOC booted
            # reports no dimensions. The first frame that is read sets the shape.
            shape = self.arraydesc.shape
        self.arraydesc = self._array_desc(shape, dtype)

    def _describe(self):
        """Return the shape and dtype of the frame in the plugin.

        The shape is None if the plugin holds no frame.
        """
        ndims = int(self._epics.get_channel_value("image_ndims") or 0)
        if ndims > MAX_DIMENSIONS:
            raise CommunicationError(
                self, f"the image plugin reports {ndims} dimensions"
            )
        # ArraySize0 is the fastest-varying dimension, which numpy expects last.
        shape = tuple(
            int(self._epics.get_channel_value(f"image_dim{i}"))
            for i in reversed(range(ndims))
        )
        data_type = self._epics.get_channel_value("image_datatype")
        try:
            # The IOC reports type names like UInt16.
            dtype = numpy.dtype(str(data_type).lower())
        except TypeError:
            raise CommunicationError(
                self, f"the image plugin reports the unknown data type {data_type!r}"
            ) from None
        return (shape if shape and all(shape) else None), dtype

    def _read_frame(self):
        """Return the frame in the plugin with the data type the plugin declares.

        The ADOrca IOCs carry UInt16 arrays in a LONG waveform, so the cast is
        needed.
        """
        shape, dtype = self._describe()
        frame = numpy.asarray(self._epics.get_channel_value("image_data"))
        if shape is None or frame.size != int(numpy.prod(shape)):
            raise CommunicationError(
                self,
                f"the image plugin delivered {frame.size} elements for the "
                f"shape {shape}",
            )
        self.arraydesc = self._array_desc(shape, dtype)
        return frame.astype(dtype, copy=False).reshape(shape)

    def _unique_id_of_this_run(self):
        """Return the uniqueId of the frame in the plugin, or None if the frame
        is older than this run.

        After ArrayCounter was reset, the frames of this run can have the
        uniqueId of the frame that the plugin held at the start. The plugin
        counts the arrays it receives, and that count tells the two apart.
        """
        received = self._epics.get_channel_value("image_received")
        unique_id = self._epics.get_channel_value("image_unique_id")
        if unique_id > self._start_counter and (
            unique_id != self._start_unique_id or received != self._start_received
        ):
            return unique_id
        return None

    def doReadArray(self, quality):
        if self._start_counter is None:
            return None  # Nothing was counted, so there is no frame of ours yet.
        if quality == FINAL:
            return self._read_last_frame()
        # LIVE sends each frame once because exposures are often longer than
        # the live interval.
        report = self.log.debug if quality == LIVE else self.log.warning
        try:
            unique_id = self._unique_id_of_this_run()
            if unique_id is None or (
                quality == LIVE and unique_id == self._live_sent_unique_id
            ):
                return None
            frame = self._read_frame()
        except (CommunicationError, TimeoutError) as err:
            report("cannot read the frame: %s", err)
            return None
        if quality == LIVE:
            self._live_sent_unique_id = unique_id
        return frame

    def _read_last_frame(self):
        """Return the last frame of this acquisition.

        The plugin works through a queue and may still be busy with it when the
        driver reports Done.
        """
        if not self._epics.get_channel_value("num_images_counter"):
            self.log.warning("no image was acquired")
            return None
        last = self._epics.get_channel_value("array_counter")
        caught_up = last > self._start_counter and self._wait_for_frame(last)
        if self._unique_id_of_this_run() is None:
            self.log.warning(
                "the image plugin received no frame of this acquisition within %s s",
                self.finishtimeout,
            )
            return None
        if not caught_up:
            self.log.warning(
                "the image plugin did not receive the last frame (%d) "
                "within %s s, so the latest frame of the plugin is used",
                last,
                self.finishtimeout,
            )
        return self._read_frame()

    def _wait_for_frame(self, last):
        """Wait until the plugin holds frame *last* of this run or a later one.

        Return False on a timeout. Every array that the plugin receives
        changes its array count, even an array with the same uniqueId.
        """
        deadline = time.monotonic() + self.finishtimeout
        while True:
            received = self._epics.get_channel_value("image_received")
            unique_id = self._unique_id_of_this_run()
            if unique_id is not None and unique_id >= last:
                return True
            try:
                self._epics.wait_for(
                    "image_received",
                    lambda count, received=received: count != received,
                    timeout=deadline - time.monotonic(),
                )
            except CommunicationError:
                return False

    def doPrepare(self):
        # A new count ends a run that was neither finished nor stopped. This
        # happens when another channel of the detector fails to start.
        self._setROParam("counting", False)
        # A run whose stop never reached the IOC would hang the count.
        if self._epics.get_channel_value("acquire_busy") == "Acquiring":
            self.log.warning("the camera is still acquiring, so it is stopped first")
            if not self._stop_acquisition():
                raise HardwareError(
                    self,
                    f"the camera is still acquiring and did not stop within "
                    f"{self.finishtimeout} s",
                )
        self._refresh_arraydesc()

    def doStart(self):
        if not self.iscontroller or not self.preselection:
            mode = CONTINUOUS
        elif self.preselection == 1:
            mode = SINGLE
        else:
            mode = MULTIPLE
            self._epics.put_channel_value("numimages_set", int(self.preselection))
        self._epics.put_channel_value("imagemode_set", mode)
        self._start_counter = self._epics.get_channel_value("array_counter")
        self._start_unique_id = self._epics.get_channel_value("image_unique_id")
        self._start_received = self._epics.get_channel_value("image_received")
        self._live_sent_unique_id = None
        self._setROParam("pausedimages", 0)
        self._start_acquisition()
        self._setROParam("counting", True)

    def _start_acquisition(self):
        """Write Acquire and wait until the IOC reports Acquiring.

        Right after the put AcquireBusy can still read Done, which the
        detector would take for "preset reached". The monitor is opened
        before the put so even a very short acquisition is seen.
        """
        started = threading.Event()

        def on_busy(update):
            if update.value == "Acquiring":
                started.set()

        counter = self._epics.get_channel_value("array_counter")
        subscription = self._epics.subscribe_channel("acquire_busy", on_busy)
        try:
            self._epics.put_channel_value("acquire", 1)
            if started.wait(self.starttimeout):
                return
        finally:
            self._epics.close_subscription(subscription)
        if self._epics.get_channel_value("array_counter") != counter:
            return  # Frames were produced, so the acquisition already finished.
        message = self._epics.get_channel_value("status_message")
        state = self._epics.get_channel_value("detector_state")
        detail = f"state {state}: {message}" if message else f"state {state}"
        raise HardwareError(
            self,
            f"the camera did not start acquiring within {self.starttimeout} s "
            f"({detail})",
        )

    def _stop_acquisition(self):
        """Write 0 to Acquire. Return False if the IOC does not report Done in time."""
        self._epics.put_channel_value("acquire", 0)
        try:
            self._epics.wait_for("acquire_busy", "Done", timeout=self.finishtimeout)
        except CommunicationError:
            return False
        return True

    def doFinish(self):
        self._setROParam("counting", False)
        # This ends a Continuous run. A Single or Multiple run has stopped already.
        if not self._stop_acquisition():
            # This is no error because the frames taken are still worth saving.
            self.log.warning(
                "the camera did not report Done within %s s", self.finishtimeout
            )

    def doStop(self):
        self._setROParam("counting", False)
        self._epics.put_channel_value("acquire", 0)

    def doPause(self):
        """Stop and restart a Continuous follower because ADCore cannot pause.

        A controller refuses to pause because a restart would count the images
        from zero again.
        """
        if self.iscontroller and self.preselection:
            return False
        self._epics.put_channel_value("acquire", 0)
        return True

    def doResume(self):
        taken = self._epics.get_channel_value("num_images_counter")
        self._setROParam("pausedimages", self.pausedimages + taken)
        self._start_acquisition()

    def valueInfo(self):
        return (Value(self.name, unit=self.unit, type="counter", fmtstr=self.fmtstr),)

    def doRead(self, maxage=0):
        images = self._epics.get_channel_value("num_images_counter")
        return [self.pausedimages + images]

    def doTime(self, preset):
        if not self.iscontroller or not self.preselection:
            return 0
        return self.preselection * (self.acquireperiod or self.acquiretime or 0)

    def doSimulate(self, preset):
        return [self.preselection if self.iscontroller else 0]

    def _status_snapshot(self, maxage):
        # EpicsDeviceBase asks subclasses to leave this method alone, but
        # _compute_status never sees a lost connection, so the camera status
        # is changed here.
        camera = EpicsDeviceBase._status_snapshot(self, maxage)
        if self.counting and camera == LOST_CONNECTION_STATUS:
            # Without a connection the end of the run cannot be seen, so the
            # count waits for the connection to come back.
            return status.BUSY, camera[1]
        return camera

    def _compute_status(self, maxage=0):
        state = self._read_channel_cached("detector_state", maxage=maxage)
        if state not in DETECTOR_STATE_STATUS:
            # AcquireBusy still tells whether the camera acquires.
            camera = status.WARN, f"unknown detector state {state!r}"
        elif state == "Error":
            message = self._read_channel_cached("status_message", maxage=maxage)
            # The driver keeps Error until the next start, and an error status
            # would make NICOS refuse that start. So Error is only a warning
            # outside a run.
            severity = status.ERROR if self.counting else status.WARN
            camera = severity, f"Error: {message}" if message else "Error"
        else:  # Every Continuous run ends in "Aborted".
            code = DETECTOR_STATE_STATUS[state]
            camera = code, "" if code == status.OK else state
        busy = self._read_channel_cached("acquire_busy", maxage=maxage)
        return worst_status(
            camera,
            (status.BUSY, "acquiring") if busy == "Acquiring" else (status.OK, ""),
            self._read_primary_alarm(maxage=maxage),
        )

    def _put_setting(self, name, value):
        """Write a `setting_channels` record. An enum choice is written as its index."""
        if isinstance(value, str):
            value = self._epics.get_channel_value_choices(f"{name}_rbv").index(value)
        self._epics.put_channel_value(f"{name}_set", value)

    doReadImagemode, doWriteImagemode = setting_methods("imagemode")
    doReadNumimages, doWriteNumimages = setting_methods("numimages")
    doReadAcquiretime, doWriteAcquiretime = setting_methods("acquiretime")
    doReadAcquireperiod, doWriteAcquireperiod = setting_methods("acquireperiod")
    doReadNumexposures, doWriteNumexposures = setting_methods("numexposures")
    doReadArrayrate = reader("array_rate")
    doReadDatatype = reader("image_datatype")
    doReadDroppedarrays = reader("image_dropped")

    def doReadUnit(self):
        return "images"
