from nicos.core import (
    Attach,
    Moveable,
    Override,
    Param,
    Value,
    floatrange,
    multiStatus,
    tupleof,
)


class VirtualHexapod(Moveable):
    """Virtual Hexapod with six axes of movement"""

    parameters = {
        "t_speed": Param(
            "Virtual translation speed",
            settable=True,
            type=floatrange(0.01, 20),
            default=1,
            unit="mm/s",
        ),
        "r_speed": Param(
            "Virtual rotation speed",
            settable=True,
            type=floatrange(0.001, 1.5),
            default=0.01,
            unit="deg/s",
        ),
    }

    parameter_overrides = {
        "fmtstr": Override(default="[%.3f, %.3f, %.3f, %.3f, %.3f, %.3f]"),
        "unit": Override(default="", mandatory=False, settable=True),
    }

    axis_names = ("tx", "ty", "tz", "rx", "ry", "rz")
    valuetype = tupleof(float, float, float, float, float, float)
    attached_devices = {name: Attach(name, Moveable) for name in axis_names}

    def doInit(self, mode):
        self._setSpeed(self.t_speed, "mm")
        self._setSpeed(self.r_speed, "deg")

    def doStart(self, target):
        for name, target in zip(self.axis_names, target):
            self._adevs[name].start(target)

    def doRead(self, maxage=0):
        pos = [self._adevs[name].read(maxage) for name in self.axis_names]
        return pos

    def doStatus(self, maxage=0):
        return multiStatus(self._adevs, maxage=maxage)

    def doIsAllowed(self, target):
        for name, pos in zip(self.axis_names, target):
            ok, why = self._adevs[name].isAllowed(pos)
            if not ok:
                return ok, f"{name} {why}"
        return ok, why

    def _setSpeed(self, speed, unit):
        for name in self.axis_names:
            if unit in self._adevs[name].unit.lower():
                self._adevs[name]._setROParam("speed", speed)

    def doWriteT_Speed(self, speed):
        self._setSpeed(speed, "mm")

    def doWriteR_Speed(self, speed):
        self._setSpeed(speed, "deg")

    def valueInfo(self):
        return [
            Value(name.capitalize(), unit=f"{self._adevs[name].unit}", fmtstr="%.3f")
            for name in self.axis_names
        ]


class TableHexapod(VirtualHexapod):
    """Hexapod with additional movement stage attached to it"""

    attached_devices = {
        "table": Attach("Table", Moveable),
    }

    parameter_overrides = {
        "fmtstr": Override(default="[%.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f]"),
    }

    axis_names = ("tx", "ty", "tz", "rx", "ry", "rz", "table")
    valuetype = tupleof(float, float, float, float, float, float, float)
