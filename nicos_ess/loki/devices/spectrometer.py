# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2022 by the NICOS contributors (see AUTHORS)
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
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************
import time

import numpy as np

from nicos import session
from nicos.core import (
    LIVE,
    POLLER,
    SIMULATION,
    ArrayDesc,
    InvalidValueError,
    Override,
    Param,
    Value,
    anytype,
    dictof,
    floatrange,
    listof,
    multiStatus,
    oneof,
    pvname,
    status,
)
from nicos.devices.epics.pva import EpicsDevice
from nicos.devices.epics.status import SEVERITY_TO_STATUS, STAT_TO_STATUS
from nicos.devices.generic import Detector, PassiveChannel
from nicos.utils import byteBuffer


class OceanInsightSpectrometer(EpicsDevice, PassiveChannel):
    """
    Device that controls and acquires data from an Ocean Insight* spectrometer.

    * formerly Ocean Optics.
    """

    parameters = {
        "pv_root": Param(
            "Spectrometer EPICS prefix",
            type=pvname,
            mandatory=True,
        ),
        "iscontroller": Param(
            "If this channel is an active controller",
            type=bool,
            settable=True,
            default=True,
        ),
        "integrationtime": Param(
            "Spectrometer integration time (ms).",
            type=int,
            default=False,
            volatile=True,
            settable=True,
            userparam=True,
        ),
        "boxcarwidth": Param(
            "Boxcar width for spectrum.",
            type=int,
            default=False,
            volatile=True,
            settable=True,
            userparam=True,
        ),
        "averages": Param(
            "Number of averages (?)",
            type=int,
            default=1,
            volatile=True,
            settable=True,
            userparam=True,
        ),
        "acquiremode": Param(
            "Acquisition mode",
            type=oneof("single", "continuous"),
            default="single",
            settable=True,
            userparam=True,
        ),
        "lightvalid": Param(
            "Whether the light background was collected with the current " "parameters",
            type=bool,
            default=False,
            volatile=True,
            settable=True,
            mandatory=False,
            userparam=False,
        ),
        "darkvalid": Param(
            "Whether the dark background was collected with the current " "parameters",
            type=bool,
            default=False,
            volatile=True,
            settable=True,
            mandatory=False,
            userparam=False,
        ),
        "lightsettings": Param(
            "Stores the settings of the last background measurement " "taken",
            type=dictof(str, anytype),
            default={},
            settable=True,
            userparam=False,
        ),
        "darksettings": Param(
            "Stores the settings of the last dark current measurement " "taken",
            type=dictof(str, anytype),
            default={},
            settable=True,
            userparam=False,
        ),
        "dark_background": Param(
            "The current dark background array",
            type=listof(float),
            settable=True,
            userparam=False,
        ),
        "light_background": Param(
            "The current light background array",
            type=listof(float),
            settable=True,
            userparam=False,
        ),
        "acquireunits": Param(
            "The units for acquire time",
            type=str,
            default="ms",
            mandatory=False,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "unit": Override(default="", settable=False, mandatory=False),
        "fmtstr": Override(default="%d"),
    }

    _record_fields = {
        "readpv": "NrSpec-RB",
        "connection_status": "Connection",
        "acquire_status": "AcqStatus-RB",
        "acquire_status.STAT": "AcqStatus-RB.STAT",
        "acquire_status.SEVR": "AcqStatus-RB.SEVR",
        "acquire_start": "AcqMode-S",
        "spectrum": "Spectrum-R",
        "xaxis": "Wavelength-R",
        "integrationtime": "IntegrationTime-S",
        "integrationtime_rbv": "IntegrationTime-RB",
        "boxcarwidth": "BoxcarWidth-S",
        "boxcarwidth_rbv": "BoxcarWidth-RB",
        "averages": "Averages-S",
        "averages_rbv": "Averages-RB",
        "dark_acquire": "GetDarkCurrent-S",
        "dark_spectrum": "DcSpectrum-R",
    }

    _detector_collector_name = ""
    _spectrum_array = None
    _wavelengths = None
    _last_update = 0
    _plot_update_delay = 0.25

    def doPreinit(self, mode):
        EpicsDevice.doPreinit(self, mode)
        if mode != SIMULATION and session.sessiontype != POLLER:
            # When daemon (re)starts force the light and dark backgrounds to be
            # invalid as we don't know what settings were used to generate
            # the spectrums currently in the IOC.
            self.lightsettings = {}
            self.darksettings = {}

    def _get_status_parameters(self):
        return {"spectrum", "acquire_status", "dark_spectrum"}

    def _update_status(self, new_status, message):
        self._current_status = new_status, message
        self._cache.put(self._name, "status", self._current_status, time.time())

    def doRead(self, maxage=0):
        return 0

    def doReadArray(self, quality):
        return self._spectrum_array

    def status_change_callback(
        self, name, param, value, units, severity, message, **kwargs
    ):
        if param == "spectrum":
            self._spectrum_array = value
            if (
                self.acquiremode == "single"
                or time.monotonic() >= self._last_update + self._plot_update_delay
            ):
                self.putResult(LIVE, value, "normal")
                self._last_update = time.monotonic()

        EpicsDevice.status_change_callback(
            self, name, param, value, units, severity, message, **kwargs
        )

    def valueInfo(self):
        return (Value(self.name, fmtstr="%d"),)

    def arrayInfo(self):
        return ArrayDesc(
            self.name,
            shape=self._spectrum_array.shape,
            dtype=self._spectrum_array.dtype,
        )

    def putResult(self, quality, data, array_type):
        databuffer = [byteBuffer(np.ascontiguousarray(data))]
        datadesc = [
            dict(
                dtype=data.dtype.str,
                shape=data.shape,
                labels={
                    "x": {
                        "define": "array",
                        "index": 0,
                        "dtype": "<f4",
                    },
                },
                plotcount=1,
                array_type=array_type,
            )
        ]
        if databuffer:
            parameters = dict(
                uid=0,
                time=time.time(),
                det=self.name,
                tag=LIVE,
                datadescs=datadesc,
            )
            self._wavelengths = self._get_pv("xaxis")
            labelbuffers = [
                byteBuffer(
                    np.ascontiguousarray(np.array(self._wavelengths).astype(np.float32))
                )
            ]
            session.updateLiveData(parameters, databuffer, labelbuffers)

    def _get_pv_parameters(self):
        return set(self._record_fields.keys())

    def _get_pv_name(self, pvparam):
        pv_name = self._record_fields.get(pvparam)
        if pv_name:
            return self.pv_root + pv_name
        return getattr(self, pvparam)

    def doStart(self):
        self.doAcquire()

    def doAcquire(self):
        if self.acquiremode == "single":
            self._put_pv("acquire_start", 1)
        else:
            self._put_pv("acquire_start", 2)

    def doFinish(self):
        self.doStop()

    def doStop(self):
        self._put_pv("acquire_start", 0)

    def doStatus(self, maxage=0):
        if not self._get_pv("connection_status"):
            return status.ERROR, "No connection to device"

        status_msg = self._get_pv("acquire_status", True)
        state = status.BUSY if status_msg == "Acquiring" else status.OK

        alarm_status = STAT_TO_STATUS.get(
            self._get_pv("acquire_status.STAT"), status.UNKNOWN
        )
        if alarm_status != status.OK:
            severity = SEVERITY_TO_STATUS.get(
                self._get_pv("acquire_status.SEVR"), status.UNKNOWN
            )
            self._write_alarm_to_log(status_msg, severity, alarm_status)
            return severity, "Alarm message"

        return state, status_msg

    def _write_alarm_to_log(self, message, severity, stat):
        msg_format = "%s (%s)"
        if severity in [status.ERROR, status.UNKNOWN]:
            self.log.error(msg_format, message, stat)
        elif severity == status.WARN:
            self.log.warning(msg_format, message, stat)

    def doReadIntegrationtime(self):
        return self._get_pv("integrationtime_rbv")

    def doWriteIntegrationtime(self, value):
        self._put_pv("integrationtime", value)

    def doReadBoxcarwidth(self):
        return self._get_pv("boxcarwidth_rbv")

    def doWriteBoxcarwidth(self, value):
        self._put_pv("boxcarwidth", value)

    def doReadAverages(self):
        return self._get_pv("averages_rbv")

    def doWriteAverages(self, value):
        self._put_pv("averages", value)

    def _get_current_settings(self):
        return {
            "integration_time": self._get_pv("integrationtime_rbv"),
            "average_spectra": self._get_pv("averages_rbv"),
            "boxcar_width": self._get_pv("boxcarwidth_rbv"),
        }

    def save_dark_background(self):
        self.darksettings = self._get_current_settings()
        self.dark_background = self._spectrum_array
        self.putResult(LIVE, self._spectrum_array, "darkbackground")

    def doReadDarkvalid(self):
        if not self.darksettings:
            return False
        return self.darksettings == self._get_current_settings()

    def save_light_background(self):
        self.lightsettings = self._get_current_settings()
        self.light_background = self._spectrum_array
        self.putResult(LIVE, self._spectrum_array, "lightbackground")

    def doReadLightvalid(self):
        if not self.lightsettings:
            return False
        return self.lightsettings == self._get_current_settings()

    def doPoll(self, n, maxage):
        self._pollParam("lightvalid")
        self._pollParam("darkvalid")


class SpectrometerCollector(Detector):
    """
    A device class that collects the area detectors present in the instrument
    setup.
    """

    parameter_overrides = {
        "unit": Override(default="progress", settable=False, mandatory=False),
        "fmtstr": Override(default="%d"),
        "liveinterval": Override(type=floatrange(0.5), default=1, userparam=True),
        "pollinterval": Override(default=1, userparam=True, settable=False),
        "statustopic": Override(default="", mandatory=False),
    }

    def doPreinit(self, mode):
        presetkeys = {"t"}
        for monitor_channel in self._attached_monitors:
            presetkeys.add(monitor_channel.name)
            monitor_channel._detector_collector_name = self.name
        self._presetkeys = presetkeys
        self._channels = self._attached_monitors

    def _collectControllers(self):
        pass

    def doSetPreset(self, **preset):
        if not preset:
            # keep old settings
            return
        for i in preset:
            if i not in self._presetkeys:
                valid_keys = ", ".join(self._presetkeys)
                raise InvalidValueError(
                    self, f"unrecognised preset {i}, should" f" one of {valid_keys}"
                )
        if "t" in preset and len(self._presetkeys.intersection(preset.keys())) > 1:
            raise InvalidValueError(
                self,
                "Cannot set number of detector counts" " and a time interval together",
            )
        self._presets = preset.copy()

    def doStatus(self, maxage=0):
        curstatus = self._cache.get(self, "status")
        if curstatus and curstatus[0] == status.ERROR:
            return curstatus
        return multiStatus(self._attached_monitors, maxage)

    def doRead(self, maxage=0):
        return []

    def doReadArrays(self, quality):
        return [monitor.doReadArray(quality) for monitor in self._attached_monitors]

    def duringMeasureHook(self, elapsed):
        if self.liveinterval is not None:
            if elapsed > self._last_live + self.liveinterval:
                self._last_live = elapsed
                return LIVE
        return None

    def doReset(self):
        pass

    def arrayInfo(self):
        return tuple(monitor.arrayInfo() for monitor in self._attached_monitors)

    def doTime(self, preset):
        return 0
