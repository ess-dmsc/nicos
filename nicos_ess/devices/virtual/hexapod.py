import numpy as np

from nicos.core import (
    Attach,
    Moveable,
    Override,
    Param,
    Value,
    floatrange,
    limits,
    multiStatus,
    oneof,
    tupleof,
)
from nicos.devices.abstract import Motor
from nicos.devices.generic import VirtualMotor


class VirtualHexapod(Moveable):
    """Virtual Hexapod with six axis of movement"""

    parameter_overrides = {
        "fmtstr": Override(default="[%.3f, %.3f, %.3f, %.3f, %.3f]"),
        "unit": Override(default="", mandatory=False, settable=True),
    }

    axis_names = ("tx", "ty", "tz", "rx", "ry", "rz")  # Tupule of default hexapod names
    valuetype = tupleof(float, float, float, float, float, float)
    attached_devices = {name: Attach(name, Moveable) for name in axis_names}

    def _readPos(self, maxage):
        pos = [self._adevs[name].read(maxage) for name in self.axis_names]
        return pos

    def doStart(self, target):
        for name, target in zip(self.axis_names, target):
            self._adevs[name].start(target)

    def doRead(self, maxage=0):
        return self._readPos(maxage)

    def doStatus(self, maxage=0):
        return multiStatus(self._adevs, maxage=maxage)

    def doIsAllowed(self, target):
        for name, pos in zip(self.axis_names, target):
            ok, why = self._adevs[name].isAllowed(pos)
            if not ok:
                return ok, f"{name} {why}"
        return ok, why

    def valueInfo(self):
        return (
            Value("Tx", unit="mm", fmtstr="%.3f"),
            Value("Ty", unit="mm", fmtstr="%.3f"),
            Value("Tz", unit="mm", fmtstr="%.3f"),
            Value("Rx", unit="deg", fmtstr="%.3f"),
            Value("Ry", unit="deg", fmtstr="%.3f"),
            Value("Rz", unit="deg", fmtstr="%.3f"),
        )
