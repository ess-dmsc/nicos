from nicos_ess.devices.epics.pva.motor import EpicsMotor
from nicos.devices.epics.pva import EpicsDevice
from nicos.devices.abstract import MappedMoveable
from nicos.core import (
    Attach,
    Moveable,
    Override,
    Value,
    tupleof,
    Param,
    pvname,
    SIMULATION,
    status,
)


class NewportLimitsWrapper(MappedMoveable):
    """Wrapper device to verify posisions sent to the hexapod by the user"""


class NewportHexapod(EpicsDevice, Moveable):
    """Virtual Hexapod with six axes of movement"""

    parameters = {
        "pv_root": Param(
            "Root of the Newport Hexapod",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "fmtstr": Override(default="[%.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f]"),
        "unit": Override(mandatory=False, settable=False),
    }

    _record_fields = {
        "status": "STATUS",
        "writepv": "MOVE_ALL",
    }

    axis_names = ("tx", "ty", "tz", "rx", "ry", "rz", "gmt")
    valuetype = tupleof(float, float, float, float, float, float, float)
    attached_devices = {name: Attach(name, EpicsMotor) for name in axis_names}

    def doInit(self, mode):
        if mode == SIMULATION:
            return

        EpicsDevice.doInit(self, mode)

    def _get_pv_name(self, pvparam):
        return f"{self.pv_root}{self._record_fields[pvparam]}"

    def _read_pv(self, name, as_string=False):
        return self._epics_wrapper.get_pv_value(name, as_string)

    def _set_pv(self, name, value):
        self._epics_wrapper.put_pv_value(self._get_pv_name(name, value))

    def doStart(self, target):
        hexapod_target = target[:-1]
        goniometer_target = target[6]
        self._set_pv(self._get_pv_name("writepv"), hexapod_target)
        # goniometer is separate from actual hexapod
        self._adevs["gmt"].start(goniometer_target)

    def doRead(self, maxage=0):
        pos = [self._adevs[name].read(maxage) for name in self.axis_names]
        return pos

    def doStatus(self, maxage=0):
        error = self._read_pv(self._get_pv_name("status"))
        if error in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 50, 63]:
            if error == 2:
                return status.ERROR, "E-STOP"
            return status.ERROR, error
        msg = self._read_pv(f"{self._get_pv_name('status')}", as_string=True)

        return status.OK, msg

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
