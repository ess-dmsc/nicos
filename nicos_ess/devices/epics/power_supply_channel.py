import threading

from nicos.core import (
    Attach,
    Override,
    Param,
    status,
    CanDisable,
    pvname,
)
#from nicos.core import POLLER, Moveable, Override, Param, oneof, pvname, status
from nicos.devices.abstract import MappedMoveable, MappedReadable, Readable

from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class PowerSupplyChannel(EpicsParameters, CanDisable, MappedReadable):
    parameters = {
        "board": Param("Power supply board"),
        "channel": Param("Power supply channel"),
        "ps_pv": Param("Power supply record PV.",
            type=pvname,
            mandatory=True,
        ),
        "voltage_monitor": Param("Voltage monitor readback value", 
            volatile=True,
            # Not sure if setting internal and userparam are making a difference.
            # Setting them anyway just for readability.
            internal=True,
            userparam=True, 
        ),
    }
    attached_devices = {
        "voltage": Attach("Monitored voltage", Readable),
        "current": Attach("Monitored current", Readable),
        "status": Attach(
            "Status of the power in the power supply channel",
            MappedReadable,
        ),
        "power_control": Attach("Control of the power supply channel", MappedMoveable),
    }

    parameter_overrides = {
        "fmtstr": Override(default="%s"),
        "unit": Override(mandatory=False),
        "mapping": Override(
            mandatory=False, settable=True, userparam=False, volatile=False
        ),
    }

    hardware_access = False
    valuetype = float

    def doPreinit(self, mode):
        """ From EpicsMotor class."""
        self._lock = threading.Lock()
        self._epics_subscriptions = []
        self._ps_status = (status.OK, "")
        self._record_fields = {
            "voltage_monitor": RecordInfo("v_mon", "-VMon", RecordType.VALUE), # Before it was BOTH
            "current_monitor": RecordInfo("i_mon", "-IMon", RecordType.BOTH),
            "power_rb": RecordInfo("pw_rb", "-Pw-RB", RecordType.STATUS),
            "power": RecordInfo("pw", "-Pw", RecordType.VALUE),
            "status_on": RecordInfo("status", "-Status-ON", RecordType.STATUS),
        }
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        # Check PV exists
        print("CHECK PV EXISTS: " + self.ps_pv + "-VMon")
        self._epics_wrapper.connect_pv(self.ps_pv + "-VMon")

    def doRead(self, maxage=0):
        print("PS DO READ")
        return self.doReadVoltage_Monitor()

    def doStatus(self, maxage=0):
        # TODO: Refactor/simplify this status method
        power_stat_msg = self._attached_status.doRead()
        stat, msg = self._attached_voltage.doStatus()
        if stat == status.OK:
            if power_stat_msg == "Power is OFF":
                return status.OK, power_stat_msg
            elif power_stat_msg == "Power is ON":
                return status.OK, power_stat_msg
        else:
            return stat, msg
    
    def doEnable(self, on):
        value = "ON" if on else "OFF"
        target = self.mapping.get(value, None)
        if target is None:
            raise InvalidValueError(self, f"Position '{value}' not in mapping")

        if self._attached_power_control is not None:
            self._attached_power_control.doStart(value)
    
    def doReadVoltage_Monitor(self):
        print("DO READ VOLTAGE MON")
        #val = self._get_cached_pv_or_ask("voltage_monitor")
        # test: get direct from cache
        val = self._get_pv(param="voltage_monitor", as_string=False)

        #if not self.fmtstr:
        #    return val
        #return self.fmtstr % val
        
        # test: return unformated
        return val
    
    def _get_cached_pv_or_ask(self, param, as_string=False):
        """
        From EpicsMotor class.
        Gets the PV value from the cache if possible, else get it from the device.
        """
        print("GET CACHED OR ASK")
        return get_from_cache_or(
            self,
            param,
            lambda: self._get_pv(param, as_string),
        )

    def _get_pv(self, param, as_string=False):
        """From EpicsMotor class"""
        print("GET PV")
        return self._epics_wrapper.get_pv_value(
            f"{self.ps_pv}{self._record_fields[param].pv_suffix}", as_string
        )


class PowerSupplyBank(CanDisable, MappedReadable):
    attached_devices = {
        "ps_channels": Attach("Power Supply channel", PowerSupplyChannel, multiple=True),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False),
        "mapping": Override(
            mandatory=False, settable=True, userparam=False, volatile=False
        ),
    }

    hardware_access = False
    valuetype = bool

    def doRead(self, maxage=0):
        for ps_channel in self._attached_ps_channels:
            ps_channel_power_rbv = ps_channel._attached_power_control.doRead()
            if ps_channel_power_rbv == "ON":
                return "ON"
        return "OFF"
    
    def doEnable(self, on):
        value = "ON" if on else "OFF"
        target = self.mapping.get(value, None)
        if target is None:
            raise InvalidValueError(self, f"Position '{value}' not in mapping")

        for ps_channel in self._attached_ps_channels:
            ps_channel._attached_power_control.doStart(value)

    def doStatus(self, maxage=0):
        on_channels = 0
        num_of_channels = len(self._attached_ps_channels)
        stat = status.BUSY

        for ps_channel in self._attached_ps_channels:
            _, msg = ps_channel.doStatus()
            
            if msg == "Power is ON":
                on_channels += 1
        
        if on_channels == num_of_channels:
            msg = "Bank is ON (all channels are ON)"
            stat = status.OK
        elif on_channels > 0:
            msg = "Bank is ON ({} of {} channels are ON)".format(
                on_channels, num_of_channels
            )
        else:
            msg = "Bank is OFF (all channels are OFF)"
            stat = status.OK

        return stat, msg
            