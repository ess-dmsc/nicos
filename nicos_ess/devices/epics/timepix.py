# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Kenan Muric <kenan.muric@ess.eu>
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************
import time

import numpy

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
    pvname,
    status,
    usermethod,
)
from nicos.devices.epics.pva import EpicsDevice
from nicos.devices.epics.status import SEVERITY_TO_STATUS, STAT_TO_STATUS
from nicos.devices.generic import Detector, ImageChannelMixin, ManualSwitch
from nicos.utils import byteBuffer

PROJECTION, FLATFIELD, DARKFIELD, INVALID = 0, 1, 2, 3


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
    Device that controls and acquires data from an area detector that uses
    the Kafka plugin for area detectors.
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
        "acquiretime": Param("Exposure time ", settable=True, volatile=True),
        "acquireperiod": Param(
            "Time between exposure starts.", settable=True, volatile=True
        ),
    }

    _control_pvs = {
        "acquire_time": "AcquireTime",
        "acquire_period": "AcquirePeriod",
    }

    _record_fields = {}

    _image_array = numpy.zeros((10, 10))
    _detector_collector_name = ""
    _last_update = 0
    _plot_update_delay = 0.1

    def doPreinit(self, mode):
        if mode == SIMULATION:
            return
        self._record_fields = {
            key + "_rbv": value + "_RBV" for key, value in self._control_pvs.items()
        }
        self._record_fields.update(self._control_pvs)
        self._set_custom_record_fields()
        EpicsDevice.doPreinit(self, mode)

    def doPrepare(self):
        self._update_status(status.BUSY, "Preparing")
        self._stoprequest = False
        self._update_status(status.OK, "")
        self.arraydesc = self.arrayInfo()

    def _update_status(self, new_status, message):
        self._current_status = new_status, message
        self._cache.put(self._name, "status", self._current_status, time.time())

    def _set_custom_record_fields(self):
        self._record_fields["size_x"] = "SizeX_RBV"
        self._record_fields["size_y"] = "SizeY_RBV"
        self._record_fields["readpv"] = "NumImagesCounter_RBV"
        self._record_fields["detector_state"] = "DetectorState_RBV"
        self._record_fields["detector_state.STAT"] = "DetectorState_RBV.STAT"
        self._record_fields["detector_state.SEVR"] = "DetectorState_RBV.SEVR"
        self._record_fields["acquire"] = "Acquire"
        self._record_fields["acquire_status"] = "AcquireBusy"
        self._record_fields["image_pv"] = self.image_pv

    def _get_pv_parameters(self):
        return set(self._record_fields) | set(["image_pv"])

    def _get_pv_name(self, pvparam):
        pv_name = self._record_fields.get(pvparam)
        if "image_pv" == pvparam:
            return self.image_pv
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
        data_type = numpy.uint16
        self.arraydesc = ArrayDesc(self.name, shape=shape, dtype=data_type)

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
            session.updateLiveData(parameters, databuffer, labelbuffers)

    def status_change_callback(
        self, name, param, value, units, severity, message, **kwargs
    ):
        if param == "readpv":
            if time.monotonic() >= self._last_update + self._plot_update_delay:
                dataarray = self._get_pv("image_pv")
                self.log.info("got data array")
                shape = self.arrayInfo().shape
                dataarray = dataarray.reshape(shape)
                self.log.info("reshaped data array")
                self.putResult(LIVE, dataarray, time.time())
                self.log.info("put result")
                self._last_update = time.monotonic()

        EpicsDevice.status_change_callback(
            self, name, param, value, units, severity, message, **kwargs
        )

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
        return alarm_severity, "%s" % detector_state

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
        self._stoprequest = True
        self._put_pv("acquire", 0)

    def doRead(self, maxage=0):
        return self._get_pv("readpv")

    def doReadArray(self, quality):
        return self._image_array

    def doReadAcquiretime(self):
        return self._get_pv("acquire_time_rbv")

    def doWriteAcquiretime(self, value):
        self._put_pv("acquire_time", value)

    def doReadAcquireperiod(self):
        return self._get_pv("acquire_period_rbv")

    def doWriteAcquireperiod(self, value):
        self._put_pv("acquire_period", value)


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
