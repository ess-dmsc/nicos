import random
import time

import numpy as np
from numpy import exp

from nicos.core import (
    Param,
    Override,
    status,
    HasOffset,
    CanDisable,
    floatrange,
    tupleof,
    MASTER,
    MoveError,
    InvalidValueError,
    listof,
)
from nicos.devices.abstract import Motor
from nicos.utils import createThread


class VirtualChopperDelay(HasOffset, CanDisable, Motor):
    parameters = {
        "speed": Param(
            "Virtual speed of the device",
            settable=True,
            type=floatrange(0, 1e6),
            unit="main/s",
        ),
        "jitter": Param("Jitter of the read value", default=0, unit="main"),
        "curvalue": Param("Current value", settable=True, unit="main"),
        "curstatus": Param(
            "Current status",
            type=tupleof(int, str),
            settable=True,
            default=(status.OK, "idle"),
            no_sim_restore=True,
        ),
        "ramp": Param(
            "Virtual speed of the device",
            settable=True,
            type=floatrange(0, 1e6),
            unit="main/min",
            volatile=True,
            no_sim_restore=True,
        ),
        "delay_errors": Param(
            "List of errors", type=listof(float), settable=True, unit="main", default=[]
        ),
        "window_size": Param(
            "Size of the error window", type=int, settable=True, default=1000
        ),
        "frequency": Param(
            "Frequency of the device",
            settable=True,
            type=float,
            unit="Hz",
            default=14.0,
        ),
        "slit_edges": Param(
            "Slit edges",
            type=listof(listof(float)),
            settable=True,
            default=[],
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, default="ns"),
        "jitter": Override(default=0.1),
        "curvalue": Override(default=10),
        "precision": Override(default=0.01),
    }

    _thread = None
    _error_thread = None

    def doInit(self, mode):
        if mode == MASTER:
            if self.target is not None:
                self._setROParam("curvalue", self.target + self.offset)
            else:
                self._setROParam("target", self.curvalue - self.offset)
        _error_thread = createThread("vitrual motor error", self._compute_error)

    def doStart(self, target):
        if self.curstatus[0] == status.DISABLED:
            raise MoveError(self, "cannot move, motor is disabled")
        pos = float(target) + self.offset
        if self._thread:
            self._setROParam("curstatus", (status.BUSY, "waiting for stop"))
            self._stop = True
            self._thread.join()
        if self.speed != 0:
            self._setROParam("curstatus", (status.BUSY, "virtual moving"))
            self._thread = createThread(
                "virtual motor %s" % self, self.__moving, (pos,)
            )
        else:
            self.log.debug("moving to %s", pos)
            self._setROParam("curvalue", pos)
            self._setROParam("curstatus", (status.OK, "idle"))

    def _compute_error(self):
        while True:
            if self.frequency > 0:
                current_errors = list(self.delay_errors)

                current_status = self.curstatus[0]

                if current_status == status.OK:
                    noise_level = 1000
                else:
                    noise_level = 100000

                current_errors.append(np.random.normal(0, noise_level))

                while len(current_errors) > self.window_size:
                    current_errors.pop(0)

                self.delay_errors = current_errors

                time.sleep(1.0 / self.frequency)
            else:
                time.sleep(1.0)

    def doRead(self, maxage=0):
        return (self.curvalue - self.offset) + self.jitter * (0.5 - random.random())

    def doStatus(self, maxage=0):
        return self.curstatus

    def doStop(self):
        if self.speed != 0 and self._thread is not None and self._thread.is_alive():
            self._stop = True
        else:
            self._setROParam("curstatus", (status.OK, "idle"))

    def doSetPosition(self, pos):
        self._setROParam("curvalue", pos + self.offset)

    def _step(self, start, end, elapsed, speed):
        gamma = speed / 10.0
        cval = end + (start - end) * exp(-gamma * elapsed)
        if abs(cval - end) < self.precision:
            return end
        return cval

    def __moving(self, pos):
        speed = self.speed
        try:
            self._stop = False
            start = self.curvalue
            started = time.time()
            while 1:
                value = self._step(start, pos, time.time() - started, speed)
                if self._stop:
                    self.log.debug("thread stopped")
                    return
                time.sleep(0.1)
                self.log.debug("thread moving to %s", value)
                self._setROParam("curvalue", value)
                if value == pos:
                    return
        finally:
            self._stop = False
            self._setROParam("curstatus", (status.OK, "idle"))

    def doReadRamp(self):
        return self.speed * 60.0

    def doWriteRamp(self, value):
        self.speed = value / 60.0

    def doEnable(self, on):
        if not on:
            if self.curstatus[0] != status.OK:
                raise InvalidValueError(self, "cannot disable busy device")
            self.curstatus = (status.DISABLED, "disabled")
        else:
            if self.curstatus[0] == status.DISABLED:
                self.curstatus = (status.OK, "idle")
