from nicos.core import SIMULATION, Override, Param, intrange, pvname, status
from nicos.devices.abstract import CanReference, Moveable
from nicos.devices.epics.pva.epics_devices import EpicsDevice
from nicos.devices.epics.status import SEVERITY_TO_STATUS


class KnauerValve(EpicsDevice, CanReference, Moveable):
    valuetype = intrange(1, 16)

    parameters = {
        "pvroot": Param(
            "The root of the PV.",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
    }

    parameter_overrides = {
        # readpv and writepv are determined automatically from the base PV
        "readpv": Override(mandatory=False, userparam=False, settable=False),
        "writepv": Override(mandatory=False, userparam=False, settable=False),
        "unit": Override(mandatory=False, settable=False, default=""),
        "fmtstr": Override(default="%d"),
        "mapping": Override(mandatory=False, settable=False, userparam=False),
    }

    _record_fields = {
        "readpv": "Position-RB",
        "writepv": "Position-S",
        "errormsg": "ErrorMsg-RB",
        "status": "InstrumentState-RB",
        "home": "Rehome-S.PROC",
    }

    def doInit(self, mode):
        if mode == SIMULATION:
            return

        EpicsDevice.doInit(self, mode)

    def _get_pv_name(self, pvparam):
        return f"{self.pvroot}{self._record_fields[pvparam]}"

    def _read_pv(self, name, as_string=False):
        return self._epics_wrapper.get_pv_value(name, as_string=as_string)

    def _set_pv(self, name, value):
        self._epics_wrapper.put_pv_value(name, value)

    def doRead(self, maxage=0):
        return self._epics_wrapper.get_pv_value(self._get_pv_name("readpv"))

    def doStart(self, value):
        self._set_pv(self._get_pv_name("writepv"), value)

    def doStatus(self, maxage=0):
        error = self._read_pv(self._get_pv_name("errormsg"))
        if error:
            return status.ERROR, error

        severity = self._read_pv(f'{self._get_pv_name("status")}.SEVR')
        msg = self._read_pv(self._get_pv_name("status"), as_string=True)

        return SEVERITY_TO_STATUS[severity], "" if msg == "Idle" else msg

    def doReference(self):
        self._set_pv(self._get_pv_name("home"), 1)
        # After homing the device will be at position 1
        self._setROParam("target", 1)
        return 1
