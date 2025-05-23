from nicos.commands.basic import sleep
from nicos.core import SIMULATION, Override, Param, pvname, status, usermethod, Moveable

from nicos.devices.epics.pva import EpicsDevice


#  This device is whatever at the moment. It's more for just having something in order to test
#  the Rheometer panel and command builder.


class RheometerControl(EpicsDevice, Moveable):
    parameters = {
        "pv_root": Param(
            "The PV root for the rheometer.",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, userparam=False),
        "mapping": Override(
            mandatory=False, settable=False, userparam=False, volatile=False
        ),
    }

    _record_fields = {}
    _command_string = ""

    def doPreinit(self, mode):
        self._set_custom_record_fields()
        EpicsDevice.doPreinit(self, mode)

    def doInit(self, mode):
        if mode == SIMULATION:
            return

    def _set_custom_record_fields(self):
        self._record_fields["set_config"] = "LoadMeasConfig-S.VAL$"
        self._record_fields["read_config"] = "LoadMeasConfig-RB"
        self._record_fields["start"] = "Start"
        self._record_fields["proc_start"] = "MeasHeader-R.PROC"
        self._record_fields["init"] = "InitDevice.PROC"
        self._record_fields["konf"] = "LoadMeasSystem-S.PROC"

    def _get_pv_parameters(self):
        return set(self._record_fields)

    def _get_pv_name(self, pvparam):
        pv_name = self._record_fields.get(pvparam)
        if pv_name:
            return self.pv_root + pv_name
        return getattr(self, pvparam)

    def doStatus(self, maxage=0):
        return status.OK, ""

    def doRead(self, maxage=0):
        return self._get_pv("read_config")

    def doStop(self):
        pass

    def set_command_string(self, command_string):
        self._command_string = command_string

    def get_command_string(self):
        return self._command_string

    @usermethod
    def set_konf(self):
        self._put_pv("konf", 1)

    @usermethod
    def set_init(self):
        self._put_pv("init", 1)

    def doStart(self, target=None):
        if not self._command_string:
            self.log.warning("No intervals provided for the measurement.")
            return
        conf_list_with_q = [*self._command_string]
        conf_list_ascii = [ord(c) for c in conf_list_with_q]
        self._put_pv("set_config", conf_list_ascii)
        sleep(2)
        self._put_pv("proc_start", 1)
        sleep(1)
        self._put_pv("start", 1)
