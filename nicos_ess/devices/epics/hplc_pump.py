import time

from nicos.core import (
    Param,
    pvname,
    status,
    Attach,
    SIMULATION,
    usermethod,
    Override,
    oneof,
)
from nicos.devices.abstract import MappedMoveable
from nicos.devices.epics.pva import EpicsDevice, EpicsStringReadable


class HPLCPumpController(EpicsDevice, MappedMoveable):
    """
    Device that controls an HPLC pump.
    """

    parameters = {
        "pv_root": Param("HPLC pump EPICS prefix", type=pvname, mandatory=True),
        "max_pressure": Param(
            "Maximum pressure", type=float, settable=True, volatile=True
        ),
        "min_pressure": Param(
            "Minimum pressure", type=float, settable=True, volatile=True
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, userparam=False),
        "mapping": Override(
            mandatory=False, settable=False, userparam=False, volatile=True
        ),
    }

    _record_fields = {}

    attached_devices = {
        "status": Attach("Status of device", EpicsStringReadable),
    }

    _commands = {}
    _run_started = False

    def doPreinit(self, mode):
        self._set_custom_record_fields()
        EpicsDevice.doPreinit(self, mode)

    def doInit(self, mode):
        self._commands = {
            "start": self.start_pump,
            "volume_start": self.volume_start,
            "time_start": self.time_start,
            "stop": self.stop_pump,
        }
        MappedMoveable.doInit(self, mode)
        self.valuetype = oneof(*self._commands)

    def doPrepare(self):
        self._update_status(status.OK, "")

    def _update_status(self, new_status, message):
        self._current_status = new_status, message
        self._cache.put(self._name, "status", self._current_status, time.time())

    def _set_custom_record_fields(self):
        self._record_fields["error"] = "Error-R"
        self._record_fields["reset_error"] = "ErrorReset-S"
        self._record_fields["error_text"] = "ErrorText-R"
        self._record_fields["set_pressure_max"] = "PressureMax-S"
        self._record_fields["pressure_max_rbv"] = "PressureMax-R"
        self._record_fields["set_pressure_min"] = "PressureMin-S"
        self._record_fields["pressure_min_rbv"] = "PressureMin-R"
        self._record_fields["pump_for_time"] = "PumpForTime-S"
        self._record_fields["pump_for_volume"] = "PumpForVolume-S"
        self._record_fields["start_pump"] = "Start-S"
        self._record_fields["stop_pump"] = "Stop-S"

    def _get_pv_parameters(self):
        return set(self._record_fields)

    def _get_pv_name(self, pvparam):
        pv_name = self._record_fields.get(pvparam)
        if pv_name:
            return self.pv_root + pv_name
        return getattr(self, pvparam)

    def doStatus(self, maxage=0):
        if self._mode == SIMULATION:
            return status.OK, ""
        device_msg = self._get_pv("error_text", as_string=True)
        if device_msg not in ["No error", "[Program is Busy]"]:
            return status.ERROR, device_msg

        attached_status, attached_msg = self._attached_status.status(maxage)
        attached_read = self._attached_status.read(maxage)

        if self._run_started:
            if attached_read == "Off":
                return status.BUSY, "Starting pump"
            else:
                self._run_started = False
                return status.BUSY, attached_msg

        if attached_read != "Off":
            return status.BUSY, attached_msg

        return attached_status, attached_msg

    def doRead(self, maxage=0):
        return self._attached_status.read(maxage)

    def doReadMapping(self):
        return {cmd: i for i, cmd in enumerate(self._commands.keys())}

    def doIsAtTarget(self, pos, target):
        if self._run_started:
            return False

        if target in ["start", "volume_start", "time_start"]:
            return "Off" == self._attached_status.read(0)
        elif target == "stop":
            return "Off" != self._attached_status.read(0)

        return False

    def doStart(self, target):
        if target in self._commands:
            # if target is not 'stop':
            # self._run_started = True
            # self._update_status(status.BUSY, 'Starting pump')
            self._commands[target]()

    def doFinish(self):
        self.doStop()

    def doStop(self):
        self._put_pv("stop_pump", 1)
        self._run_started = False

    def doReset(self):
        self._put_pv("reset_error", 1)

    def doReadMax_Pressure(self, maxage=0):
        return self._get_pv("pressure_max_rbv")

    def doWriteMax_Pressure(self, value):
        self._put_pv("set_pressure_max", value)

    def doReadMin_Pressure(self, maxage=0):
        return self._get_pv("pressure_min_rbv")

    def doWriteMin_Pressure(self, value):
        self._put_pv("set_pressure_min", value)

    @usermethod
    def start_pump(self):
        """Start pumping"""
        if self._mode == SIMULATION:
            return
        # curr_status = self.status(0)[0]
        # if curr_status != status.OK:
        #    raise InvalidValueError('Cannot start from the current state, '
        #                            'please stop the pump first')
        self._run_started = True
        self._update_status(status.BUSY, "Starting pump")
        self._put_pv("start_pump", 1)

    @usermethod
    def stop_pump(self):
        """Stop pumping"""
        if self._mode == SIMULATION:
            return
        # curr_status = self.status(0)[0]
        # if curr_status != status.BUSY:
        #    raise InvalidValueError('Cannot stop from the current state, '
        #                            'please start the pump first')
        self._put_pv("stop_pump", 1)

    @usermethod
    def volume_start(self):
        """Start pumping for a given volume"""
        if self._mode == SIMULATION:
            return
        # curr_status = self.status(0)[0]
        # if curr_status != status.OK:
        #    raise InvalidValueError('Cannot start from the current state, '
        #                            'please stop the pump first')
        self._run_started = True
        self._update_status(status.BUSY, "Starting pump")
        self._put_pv("pump_for_volume", 1)

    @usermethod
    def time_start(self):
        """Start pumping for a given time"""
        if self._mode == SIMULATION:
            return
        # curr_status = self.status(0)[0]
        # if curr_status != status.OK:
        #    raise InvalidValueError('Cannot start from the current state, '
        #                            'please stop the pump first')
        self._run_started = True
        self._update_status(status.BUSY, "Starting pump")
        self._put_pv("pump_for_time", 1)
