from nicos.core import Attach, PositionError, Readable
from nicos.devices.epics.pva import EpicsMoveable
from nicos.devices.generic import ManualSwitch


class DlsPositioner(ManualSwitch, EpicsMoveable):
    """A device for controlling the Diamond Light Source's positioner for the
    EPICS motor.

    The DLS positioner allows the motor to only be moved to set positions which
    are pre-defined in the EPICS IOC.

    This device needs to be configured to have the same number of set positions
    as the IOC does.
    """

    attached_devices = {
        "motor": Attach("the underlying motor", Readable),
    }

    def doStart(self, target):
        self._put_pv("writepv", target)

    def doStatus(self, maxage=0):
        return self._attached_motor.status(maxage)

    def doRead(self, maxage=0):
        position = EpicsMoveable.doRead(self, maxage)
        if position in self.states:
            return position
        raise PositionError(self, "device is in an unknown state")

    def _get_pv_parameters(self):
        return {"readpv", "writepv"}
