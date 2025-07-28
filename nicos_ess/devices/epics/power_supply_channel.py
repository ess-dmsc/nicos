from nicos.core import (
    Attach,
    Override,
    Param,
    status,
    CanDisable,
)
from nicos.devices.abstract import MappedMoveable, MappedReadable, Readable


class PowerSupplyChannel(CanDisable, MappedReadable):
    parameters = {
        "board": Param("Power supply board"),
        "channel": Param("Power supply channel"),
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

    def doRead(self, maxage=0):
        return self._attached_voltage.doRead()

    def doStatus(self, maxage=0):
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
            