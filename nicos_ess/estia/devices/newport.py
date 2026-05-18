from time import sleep

from nicos.core import (
    Attach,
    Moveable,
    Override,
    Value,
    multiStatus,
    tupleof,
)


class NewportHexapod(Moveable):
    """Virtual Hexapod with six axes of movement"""

    parameter_overrides = {
        "fmtstr": Override(default="[%.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f]"),
        "unit": Override(default="", mandatory=False, settable=True),
    }

    axis_names = ("tx", "ty", "tz", "rx", "ry", "rz", "gmt")
    valuetype = tupleof(float, float, float, float, float, float, float)
    attached_devices = {name: Attach(name, Moveable) for name in axis_names}

    def doStart(self, target):
        # Create a very small delay between axis motions to allow
        # for the controller to run the command
        # TODO: Implement MOVE_ALL pv from Newport Hexapod
        for name, input in zip(self.axis_names, target):
            self._adevs[name].start(input)
            sleep(1)

    def doRead(self, maxage=0):
        pos = [self._adevs[name].read(maxage) for name in self.axis_names]
        return pos

    def doStatus(self, maxage=0):
        # TODO: Implement STATUS pv for total hexapod status
        return multiStatus(self._adevs, maxage=maxage)

    def doIsAllowed(self, target):
        for name, pos in zip(self.axis_names, target):
            ok, why = self._adevs[name].isAllowed(pos)
            if not ok:
                return ok, f"{name} {why}"
        return ok, why

    def valueInfo(self):
        return [
            Value(name.capitalize(), unit=f"{self._adevs[name].unit}", fmtstr="%.3f")
            for name in self.axis_names
        ]
