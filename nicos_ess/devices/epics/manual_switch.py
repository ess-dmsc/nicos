from nicos.core import (
    Param,
    nonemptylistof,
    anytype,
    Override,
    oneof,
    PositionError,
    status,
)
from nicos.devices.epics.pva import EpicsMoveable


class ManualSwitch(EpicsMoveable):
    """A representation of a manually changeable device.

    This is akin to the `ManualMove` device, but for instrument parameters that
    take only discrete values.

    The `states` parameter must be a list of allowed values.
    """

    parameters = {
        "states": Param(
            "List of allowed states", type=nonemptylistof(anytype), mandatory=True
        ),
        "mapping": Param(
            "Mapping of states to values",
            type=dict,
            mandatory=False,
            settable=False,
            default={},
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False),
    }

    hardware_access = True

    def doInit(self, mode):
        self.valuetype = oneof(*self.states)

    def doReadTarget(self):
        target = self._get_pv("writepv")
        for state, value in self.mapping.items():
            if target == value:
                return state

    def doStart(self, target):
        value = self.mapping.get(target, None)
        if value is None:
            return
        self._put_pv("writepv", value)
        self.read()

    def doRead(self, maxage=0):
        if self.target in self.states:
            return self.target
        raise PositionError(self, "device is in an unknown state")

    def doStatus(self, maxage=0):
        return status.OK, ""

    def doIsAllowed(self, target):
        if target in self.states:
            return True, ""
        return False, "%r is not in %r" % (target, self.states)
