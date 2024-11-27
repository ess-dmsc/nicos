import threading
import time
from enum import Enum

import numpy
from streaming_data_types import deserialise_ADAr, deserialise_ad00

from nicos import session
from nicos.core import (
    LIVE,
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
    pvname,
    status,
    usermethod,
    Attach,
)
from nicos.devices.epics.pva import EpicsDevice
from nicos.devices.epics.status import SEVERITY_TO_STATUS, STAT_TO_STATUS
from nicos.devices.generic import Detector, ImageChannelMixin, ManualSwitch
from nicos.utils import byteBuffer, createThread
from nicos_ess.devices.epics.pva import EpicsMappedMoveable, EpicsAnalogMoveable

deserialiser_by_schema = {
    "ADAr": deserialise_ADAr,
    "ad00": deserialise_ad00,
}

data_type_t = {
    "Int8": numpy.int8,
    "UInt8": numpy.uint8,
    "Int16": numpy.int16,
    "UInt16": numpy.uint16,
    "Int32": numpy.int32,
    "UInt32": numpy.uint32,
    "Int64": numpy.int64,
    "UInt64": numpy.uint64,
    "Float32": numpy.float32,
    "Float64": numpy.float64,
}

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


class CoolingMode(Enum):
    OFF = 0
    ON = 1
    MAX = 2


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


class AreaDetector(EpicsDevice, ImageChannelMixin, Measurable):
    """
    Device that controls and acquires data from an area detector.
    """

    parameters = {
        "pv_root": Param("Area detector EPICS prefix", type=pvname, mandatory=True),
        "image_pv": Param("Image PV name", type=pvname, mandatory=True),
        "iscontroller": Param(
            "If this channel is an active controller",
            type=bool,
            settable=True,
            default=True,
        ),
        "topicpv": Param(
            "Topic pv name where the image is.",
            type=str,
            mandatory=True,
            settable=False,
            default=False,
        ),
        "sourcepv": Param(
            "Source pv name for the image data on the topic.",
            type=str,
            mandatory=True,
            settable=False,
            default=False,
        ),
        "imagemode": Param(
            "Mode to acquire images.",
            type=oneof("single", "multiple", "continuous"),
            settable=True,
            default="continuous",
            volatile=True,
        ),
        "binning": Param(
            "Binning factor",
            type=oneof("1x1", "2x2", "4x4"),
            settable=True,
            default="1x1",
            volatile=True,
        ),
        "subarraymode": Param(
            "Subarray of whole image active.",
            type=bool,
            settable=True,
            default=False,
            volatile=True,
        ),
        "sizex": Param("Image X size.", settable=True, volatile=True),
        "sizey": Param("Image Y size.", settable=True, volatile=True),
        "startx": Param("Image X start index.", settable=True, volatile=True),
        "starty": Param("Image Y start index.", settable=True, volatile=True),
        "binx": Param("Binning factor X", settable=True, volatile=True),
        "biny": Param("Binning factor Y", settable=True, volatile=True),
        "acquiretime": Param("Exposure time ", settable=True, volatile=True),
        "acquireperiod": Param(
            "Time between exposure starts.", settable=True, volatile=True
        ),
        "numimages": Param(
            "Number of images to take (only in imageMode=multiple).",
            settable=True,
            volatile=True,
        ),
        "numexposures": Param(
            "Number of exposures per image.", settable=True, volatile=True
        ),
    }

    _control_pvs = {
        "size_x": "SizeX",
        "size_y": "SizeY",
        "min_x": "MinX",
        "min_y": "MinY",
        "bin_x": "BinX",
        "bin_y": "BinY",
        "acquire_time": "AcquireTime",
        "acquire_period": "AcquirePeriod",
        "num_images": "NumImages",
        "num_exposures": "NumExposures",
        "image_mode": "ImageMode",
    }

    _record_fields = {}

    _image_array = numpy.zeros((10, 10))
    _detector_collector_name = ""
    _last_update = 0
    _plot_update_delay = 2.0

    def doPreinit(self, mode):
        if mode == SIMULATION:
            return
        self._record_fields = {
            key + "_rbv": value + "_RBV" for key, value in self._control_pvs.items()
        }
        self._record_fields.update(self._control_pvs)
        self._set_custom_record_fields()
        EpicsDevice.doPreinit(self, mode)
        self._image_processing_lock = threading.Lock()

    def doPrepare(self):
        self._update_status(status.BUSY, "Preparing")
        self._update_status(status.OK, "")
        self.arraydesc = self.arrayInfo()

    def _update_status(self, new_status, message):
        self._current_status = new_status, message
        self._cache.put(self._name, "status", self._current_status, time.time())

    def _set_custom_record_fields(self):
        self._record_fields["max_size_x"] = "MaxSizeX_RBV"
        self._record_fields["max_size_y"] = "MaxSizeY_RBV"
        self._record_fields["data_type"] = "DataType_RBV"
        self._record_fields["subarray_mode"] = "SubarrayMode-S"
        self._record_fields["subarray_mode_rbv"] = "SubarrayMode-RB"
        self._record_fields["binning_factor"] = "Binning-S"
        self._record_fields["binning_factor_rbv"] = "Binning-RB"
        self._record_fields["readpv"] = "NumImagesCounter_RBV"
        self._record_fields["detector_state"] = "DetectorState_RBV"
        self._record_fields["detector_state.STAT"] = "DetectorState_RBV.STAT"
        self._record_fields["detector_state.SEVR"] = "DetectorState_RBV.SEVR"
        self._record_fields["array_rate_rbv"] = "ArrayRate_RBV"
        self._record_fields["acquire"] = "Acquire"
        self._record_fields["acquire_status"] = "AcquireBusy"
        self._record_fields["image_pv"] = self.image_pv
        self._record_fields["topicpv"] = self.topicpv
        self._record_fields["sourcepv"] = self.sourcepv

    def _get_pv_parameters(self):
        return set(self._record_fields) | set(["image_pv", "topicpv", "sourcepv"])

    def _get_pv_name(self, pvparam):
        pv_name = self._record_fields.get(pvparam)
        if "image_pv" == pvparam:
            return self.image_pv
        if "topicpv" == pvparam:
            return self.topicpv
        if "sourcepv" == pvparam:
            return self.sourcepv
        if pv_name:
            return self.pv_root + pv_name
        return getattr(self, pvparam)

    def valueInfo(self):
        return (Value(self.name, fmtstr="%d"),)

    def arrayInfo(self):
        self.update_arraydesc()
        return self.arraydesc

    def update_arraydesc(self):
        shape = self._get_pv("size_y"), self._get_pv("size_x")
        binning_factor = int(self.binning[0])
        shape = (shape[0] // binning_factor, shape[1] // binning_factor)
        self._plot_update_delay = (shape[0] * shape[1]) / 2097152.0
        data_type = data_type_t[self._get_pv("data_type", as_string=True)]
        self.arraydesc = ArrayDesc(self.name, shape=shape, dtype=data_type)

    def status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if param == "readpv" and value != 0:
            if time.monotonic() >= self._last_update + self._plot_update_delay:
                _thread = createThread(f"get_image_{time.time_ns()}", self.get_image)

        EpicsDevice.status_change_callback(
            self, name, param, value, units, limits, severity, message, **kwargs
        )

    def doIsCompleted(self):
        _thread = createThread(f"get_image_{time.time_ns()}", self.get_image)

    def get_image(self):
        dataarray = self._get_pv("image_pv")
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
        detector_state = self._get_pv("acquire_status", True)
        alarm_status = STAT_TO_STATUS.get(
            self._get_pv("detector_state.STAT"), status.UNKNOWN
        )
        alarm_severity = SEVERITY_TO_STATUS.get(
            self._get_pv("detector_state.SEVR"), status.UNKNOWN
        )
        if detector_state != "Done" and alarm_severity < status.BUSY:
            alarm_severity = status.BUSY
        self._write_alarm_to_log(detector_state, alarm_severity, alarm_status)
        return alarm_severity, "%s, image mode is %s" % (detector_state, self.imagemode)

    def _write_alarm_to_log(self, pv_value, severity, stat):
        msg_format = "%s (%s)"
        if severity in [status.ERROR, status.UNKNOWN]:
            self.log.error(msg_format, pv_value, stat)
        elif severity == status.WARN:
            self.log.warning(msg_format, pv_value, stat)

    def _limit_size(self, value, max_pv):
        max_value = self._get_pv(max_pv)
        if value > max_value:
            value = max_value
        elif value < max_value:
            self.subarraymode = True
        return int(value)

    def _limit_start(self, value):
        if value < 0:
            value = 0
        elif value > 0:
            self.subarraymode = True
        return int(value)

    def check_if_max_size(self):
        if (
            self.sizex == self._get_pv("max_size_x")
            and self.sizey == self._get_pv("max_size_y")
            and self.startx == 0
            and self.starty == 0
        ):
            self.subarraymode = False

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
        self._put_pv("acquire", 1)

    def doFinish(self):
        self.doStop()

    def doStop(self):
        self._put_pv("acquire", 0)

    def doRead(self, maxage=0):
        return self._get_pv("readpv")

    def doReadArray(self, quality):
        return self._image_array

    def doReadSizex(self):
        return self._get_pv("size_x_rbv")

    def doWriteSizex(self, value):
        self._put_pv("size_x", self._limit_size(value, "max_size_x"))
        self.check_if_max_size()

    def doReadSizey(self):
        return self._get_pv("size_y_rbv")

    def doWriteSizey(self, value):
        self._put_pv("size_y", self._limit_size(value, "max_size_y"))
        self.check_if_max_size()

    def doReadStartx(self):
        return self._get_pv("min_x_rbv")

    def doWriteStartx(self, value):
        self._put_pv("min_x", self._limit_start(value))

    def doReadStarty(self):
        return self._get_pv("min_y_rbv")

    def doWriteStarty(self, value):
        self._put_pv("min_y", self._limit_start(value))

    def doReadAcquiretime(self):
        return self._get_pv("acquire_time_rbv")

    def doWriteAcquiretime(self, value):
        self._put_pv("acquire_time", value)

    def doReadAcquireperiod(self):
        return self._get_pv("acquire_period_rbv")

    def doWriteAcquireperiod(self, value):
        self._put_pv("acquire_period", value)

    def doReadBinx(self):
        return self._get_pv("bin_x_rbv")

    def doWriteBinx(self, value):
        self._put_pv("bin_x", value)

    def doReadBiny(self):
        return self._get_pv("bin_y_rbv")

    def doWriteBiny(self, value):
        self._put_pv("bin_y", value)

    def doReadNumimages(self):
        return self._get_pv("num_images_rbv")

    def doWriteNumimages(self, value):
        self._put_pv("num_images", value)

    def doReadNumexposures(self):
        return self._get_pv("num_exposures_rbv")

    def doWriteNumexposures(self, value):
        self._put_pv("num_exposures", value)

    def doWriteImagemode(self, value):
        self._put_pv("image_mode", ImageMode[value.upper()].value)

    def doReadImagemode(self):
        return ImageMode(self._get_pv("image_mode")).name.lower()

    def doReadSubarraymode(self):
        return self._get_pv("subarray_mode_rbv")

    def doWriteSubarraymode(self, value):
        self._put_pv("subarray_mode", value)

    def doReadBinning(self):
        return binning_factor_map[self._get_pv("binning_factor_rbv")]

    def doWriteBinning(self, value):
        self._put_pv("binning_factor", value)

    def get_topic_and_source(self):
        return self._get_pv("topicpv", as_string=True), self._get_pv(
            "sourcepv", as_string=True
        )


class NGemDetector(EpicsDevice, ImageChannelMixin, Measurable):
    """
    Device that controls and acquires data from a nGEM detector.
    Only uses a subset of the AreaDetector parameters.
    """

    parameters = {
        "pv_root": Param("Area detector EPICS prefix", type=pvname, mandatory=True),
        "image_pv": Param("Image PV name", type=pvname, mandatory=True),
        "iscontroller": Param(
            "If this channel is an active controller",
            type=bool,
            settable=True,
            default=True,
        ),
    }

    _record_fields = {}

    _image_array = numpy.zeros((10, 10))
    _detector_collector_name = ""
    _last_update = 0
    _plot_update_delay = 2.0

    def doPreinit(self, mode):
        if mode == SIMULATION:
            return
        self._set_custom_record_fields()
        EpicsDevice.doPreinit(self, mode)
        self._image_processing_lock = threading.Lock()

    def doPrepare(self):
        self._update_status(status.BUSY, "Preparing")
        self._update_status(status.OK, "")
        self.arraydesc = self.arrayInfo()

    def _update_status(self, new_status, message):
        self._current_status = new_status, message
        self._cache.put(self._name, "status", self._current_status, time.time())

    def _set_custom_record_fields(self):
        # self._record_fields["readpv"] = "NumImagesCounter_RBV"
        # self._record_fields["array_rate_rbv"] = "ArrayRate_RBV"
        self._record_fields["acquire"] = "Acquire"
        self._record_fields["image_pv"] = self.image_pv
        # self._record_fields["topicpv"] = self.topicpv
        # self._record_fields["sourcepv"] = self.sourcepv

    def _get_pv_parameters(self):
        return set(self._record_fields) | set(["image_pv"])

    def _get_pv_name(self, pvparam):
        pv_name = self._record_fields.get(pvparam)
        if "image_pv" == pvparam:
            return self.image_pv
        # if "topicpv" == pvparam:
        #     return self.topicpv
        # if "sourcepv" == pvparam:
        #     return self.sourcepv
        if pv_name:
            return self.pv_root + pv_name
        return getattr(self, pvparam)

    def valueInfo(self):
        return (Value(self.name, fmtstr="%d"),)

    def arrayInfo(self):
        self.update_arraydesc()
        return self.arraydesc

    def update_arraydesc(self):
        shape = 128, 128
        binning_factor = 1
        shape = (shape[0] // binning_factor, shape[1] // binning_factor)
        self._plot_update_delay = (shape[0] * shape[1]) / 2097152.0
        data_type = numpy.uint16
        self.arraydesc = ArrayDesc(self.name, shape=shape, dtype=data_type)

    def status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if param == "readpv" and value != 0:
            if time.monotonic() >= self._last_update + self._plot_update_delay:
                _thread = createThread(f"get_image_{time.time_ns()}", self.get_image)

        EpicsDevice.status_change_callback(
            self, name, param, value, units, limits, severity, message, **kwargs
        )

    def doIsCompleted(self):
        _thread = createThread(f"get_image_{time.time_ns()}", self.get_image)

    def get_image(self):
        dataarray = self._get_pv("image_pv")
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
        alarm_severity = status.OK
        detector_state = "Done" if self._get_pv("acquire") == 0 else "Acquiring"
        if detector_state != "Done":
            alarm_severity = status.BUSY
        return alarm_severity, "%s, image mode is %s" % (detector_state, self.imagemode)

    def _write_alarm_to_log(self, pv_value, severity, stat):
        msg_format = "%s (%s)"
        if severity in [status.ERROR, status.UNKNOWN]:
            self.log.error(msg_format, pv_value, stat)
        elif severity == status.WARN:
            self.log.warning(msg_format, pv_value, stat)

    def doStart(self, **preset):
        self.doAcquire()

    def doAcquire(self):
        self._put_pv("acquire", 1)

    def doFinish(self):
        self.doStop()

    def doStop(self):
        self._put_pv("acquire", 0)

    def doRead(self, maxage=0):
        # return self._get_pv("readpv")
        return 0

    def doReadArray(self, quality):
        return self._image_array

    def get_topic_and_source(self):
        return "", ""


class OrcaFlash4(AreaDetector):
    """
    Device that controls and acquires data from an Orca Flash 4 area detector.
    """

    parameters = {
        "chip_coolingmode": Param(
            "Cooling mode of the camera.",
            type=oneof("off", "on", "max"),
            settable=True,
            volatile=True,
        ),
        "chip_temperature": Param(
            "Temperature of the camera.", settable=False, volatile=True
        ),
        "watercooler_mode": Param(
            "Set if the watercooler is on or off.",
            settable=True,
            volatile=True,
            type=oneof("ON", "OFF"),
        ),
        "watercooler_temperature": Param(
            "Temperature of the water cooling the camera.", settable=True, volatile=True
        ),
    }

    attached_devices = {
        "watercooler_mode": Attach(
            "Run mode on/off", EpicsMappedMoveable, optional=True
        ),
        "watercooler_temperature": Attach(
            "Temperature of the water", EpicsAnalogMoveable, optional=True
        ),
    }

    _control_pvs = {
        "size_x": "SizeX",
        "size_y": "SizeY",
        "min_x": "MinX",
        "min_y": "MinY",
        "bin_x": "BinX",
        "bin_y": "BinY",
        "acquire_time": "AcquireTime",
        "acquire_period": "AcquirePeriod",
        "num_images": "NumImages",
        "num_exposures": "NumExposures",
        "image_mode": "ImageMode",
    }

    def _set_custom_record_fields(self):
        AreaDetector._set_custom_record_fields(self)
        self._record_fields["chip_temperature"] = "Temperature-R"
        self._record_fields["cooling_mode"] = "SensorCooler-S"
        self._record_fields["cooling_mode_rbv"] = "SensorCooler-RB"

    def doReadChip_Coolingmode(self):
        return CoolingMode(self._get_pv("cooling_mode_rbv")).name.lower()

    def doWriteChip_Coolingmode(self, value):
        if self.watercooler_mode.upper() == "OFF" and value.upper() != "OFF":
            if self._attached_watercooler_mode is None:
                self.log.warning(
                    f"Cannot set chip cooling mode to {value} "
                    f"because there is no attached cooler."
                )
                return

            self.log.warning(
                f"Cannot set chip cooling mode to {value} if water cooler is OFF."
            )
            return

        self._put_pv("cooling_mode", CoolingMode[value.upper()].value)

    def doReadChip_Temperature(self):
        return self._get_pv("chip_temperature")

    def doReadWatercooler_Mode(self):
        if self._attached_watercooler_mode is not None:
            watercooler_mode = self._attached_watercooler_mode.read()

            if (
                self.chip_coolingmode.upper() != "OFF"
                and watercooler_mode.upper() == "OFF"
            ):
                self.log.warning(
                    f"The chip cooling mode is {self.chip_coolingmode}. "
                    f"Turn it off since the water cooler is off."
                )
                self.chip_coolingmode = "off"

            return watercooler_mode

        # We don't know the value but safe to assume it is off
        return "OFF"

    def doWriteWatercooler_Mode(self, value):
        if value.upper() == "OFF" and self.chip_coolingmode.upper() != "OFF":
            self.log.warning(
                f"Cannot turn off water cooler if cooling mode "
                f"is {self.chip_coolingmode}."
            )
            return

        if self._attached_watercooler_mode is not None:
            self._attached_watercooler_mode.start(value)

    def doReadWatercooler_Temperature(self):
        if self._attached_watercooler_temperature is not None:
            return self._attached_watercooler_temperature.read()
        return -273.15

    def doWriteWatercooler_Temperature(self, value):
        if self._attached_watercooler_temperature is not None:
            self._attached_watercooler_temperature.start(value)


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
            "No array size was found for area detector " "with topic %s and source %s.",
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
