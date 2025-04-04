import time

import numpy as np

from nicos.core import (
    Attach,
    Moveable,
    Param,
    Value,
    anytype,
    dictof,
    listof,
    oneof,
)
from nicos.devices.generic import Detector, PassiveChannel, VirtualGauss


class VirtualSpectrometer(Detector, PassiveChannel):
    parameters = {
        "iscontroller": Param(
            "If this channel is an active controller",
            type=bool,
            settable=True,
            default=True,
        ),
        "integrationtime": Param(
            "Spectrometer integration time (ms).",
            type=int,
            default=1,
            volatile=False,
            settable=True,
            userparam=True,
        ),
        "boxcarwidth": Param(
            "Boxcar width for spectrum.",
            type=int,
            default=2,
            volatile=False,
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
            "Whether the light background was collected with the current parameters",
            type=bool,
            default=False,
            volatile=False,
            settable=True,
            mandatory=False,
            userparam=False,
        ),
        "darkvalid": Param(
            "Whether the dark background was collected with the current parameters",
            type=bool,
            default=False,
            volatile=False,
            settable=True,
            mandatory=False,
            userparam=False,
        ),
        "lightsettings": Param(
            "Stores the settings of the last background measurement taken",
            type=dictof(str, anytype),
            default={},
            settable=True,
            userparam=False,
        ),
        "darksettings": Param(
            "Stores the settings of the last dark current measurement taken",
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

    def doPreinit(self, mode):
        self._spec_simulator = VirtualGauss()

    def doStart(self):
        self.doAcquire()

    def doAcquire(self):
        self._spec_simulator.doStart()

    def doFinish(self):
        self.doStop()

    def doStop(self):
        self._spec_simulator.doStop()

    def doReadIntegrationtime(self):
        return self.integrationtime

    def doReadBoxcarwidth(self):
        return self.boxcarwidth

    def doReadAverages(self):
        self._spec_simulator.doRead()

    def _get_current_settings(self):
        return {
            "integration_time": self.doReadIntegrationtime(),
            "average_spectra": self.doReadAverages(),
            "boxcar_width": self.doReadBoxcarwidth(),
        }

    def save_dark_background(self):
        self.darksettings = self._get_current_settings()
        # self.dark_background = self._spectrum_array
        # self.putResult(LIVE, self._spectrum_array, "darkbackground")

    def doReadDarkvalid(self):
        if not self.darksettings:
            return False
        return self.darksettings == self._get_current_settings()

    def save_light_background(self):
        self.lightsettings = self._get_current_settings()
        # self.light_background = self._spectrum_array
        # self.putResult(LIVE, self._spectrum_array, "lightbackground")

    def doReadLightvalid(self):
        if not self.lightsettings:
            return False
        return self.lightsettings == self._get_current_settings()

    def doPoll(self, n, maxage):
        self._pollParam("lightvalid")
        self._pollParam("darkvalid")


class VirtualPassiveChannelForSpectrometer(PassiveChannel):
    attached_devices = {
        "motors": Attach(
            "Moveables on which the count depends", Moveable, multiple=True
        ),
    }

    parameters = {
        "centers": Param("Center of the gaussian", type=listof(float), settable=True),
        "stddev": Param(
            "Standard deviation of the gauss function",
            type=float,
            settable=True,
        ),
        "rate": Param(
            "Amplitude in counts/sec", type=float, settable=True, default=100.0
        ),
    }

    def doStart(self):
        self._start_time = time.time()
        self._pause_start = None
        self._pause_time = None
        self._pause_interval = 0
        PassiveChannel.doStart(self)

    def doStop(self):
        self._end_time = time.time()
        PassiveChannel.doStop(self)

    def doFinish(self):
        self._end_time = time.time()
        if self._pause_start:
            self.doResume()
        PassiveChannel.doFinish(self)

    def doPause(self):
        self._pause_start = time.time()

    def doResume(self):
        time_paused = time.time() - self._pause_start
        if self._pause_interval:
            self._pause_interval += time_paused
        else:
            self._pause_interval = time_paused

    def doRead(self, maxage=0):
        if self._end_time:
            elapsed_time = self._end_time - self._start_time
            if self._pause_interval:
                elapsed_time -= self._pause_interval
            ampl = elapsed_time * self.rate
        else:
            ampl = self.rate
        count = 1.0
        for mot, center in zip(self._attached_motors, self.centers):
            count *= max(
                1.0,
                ampl
                * np.exp(-((mot.read(maxage) - center) ** 2) / 2.0 * self.stddev**2),
            )
        return int(count)

    def valueInfo(self):
        return (
            Value(self.name, unit="cts", errors="sqrt", type="counter", fmtstr="%d"),
        )
