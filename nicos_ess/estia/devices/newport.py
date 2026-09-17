from time import sleep

from nicos.core import (
    Attach,
    Moveable,
    Override,
    Value,
    multiStatus,
    status,
    tupleof,
)
from nicos_ess.devices.epics.pva import (
    EpicsMappedMoveable,
    EpicsReadable,
    EpicsStringReadable,
)


class NewportHexapod(Moveable):
    """Virtual Hexapod with six axes of movement + Goniometer Control
    Starting the Hexapod controls it via the MOVE_ALL function from the
    controller. For individual axes control with relative motion, please use
    the Hexapod Control tab in the GUI.
    """

    parameter_overrides = {
        "fmtstr": Override(default="[%.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f]"),
        "unit": Override(default="", mandatory=False, settable=True),
    }

    status_table = {
        "OK": ([10, 11, 12, 13, 15, 16, 17, 70, 77], status.OK),
        "BUSY": ([40, 41, 44, 45, 48, 49, 68, 69, 73], status.BUSY),
        "ERROR": ([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 50, 63, 42], status.ERROR),
        "DISABLE": (
            [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 74, 75, 76],
            status.DISABLED,
        ),
    }

    valuetype = tupleof(float, float, float, float, float, float, float)

    axis_names = ("tx", "ty", "tz", "rx", "ry", "rz", "gmt")
    sp_names = ((setpoint + "_sp") for setpoint in axis_names[:-1])

    attached_devices = {name: Attach(name, Moveable) for name in axis_names}
    attached_devices.update({name: Attach(name, Moveable) for name in sp_names})
    attached_devices.update(
        {
            "move_all": Attach("move_all", EpicsMappedMoveable),
            "status": Attach("status", EpicsReadable),
            "errmsg": Attach("status", EpicsStringReadable),
        }
    )

    def doStart(self, target):
        # set all setpoints to their target position then start with move_all
        for name, input in zip(self.sp_names, target):
            self._adevs[name].start(input)
        self._adevs["move_all"].move("On")
        self._adevs["gmt"].start(target[-1])

    # stopping any axes will stop the entire hexapod, choosing to use the same axes as EPICS
    def doStop(self):
        self._adevs["tx"].stop()

    def doIsCompleted(self):
        self._adevs["move_all"].move("Off")

    def doRead(self, maxage=0):
        pos = [self._adevs[name].read(maxage) for name in self.axis_names]
        return pos

    def doStatus(self, maxage=0):
        value = self._adevs["status"].read()
        msg = self._adevs["errmsg"].read()
        for states in self.status_table:
            if value in self.status_table[states][0]:
                return (self.status_table[states][1], value)
        return (status.UNKNOWN, value, msg)

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


class OldNewportHexapod(Moveable):
    """Virtual Hexapod with six axes of movement + Goniometer Control
    Starting the Hexapod controls it by moving each axes indivitually with
    a pause between each motion. For individual axes control with relative motion,
    please use the Hexapod Control tab in the GUI.
    """

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
        for name, input in zip(self.axis_names, target):
            self._adevs[name].start(input)
            sleep(1)

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

    def valueInfo(self):
        return [
            Value(name.capitalize(), unit=f"{self._adevs[name].unit}", fmtstr="%.3f")
            for name in self.axis_names
        ]
