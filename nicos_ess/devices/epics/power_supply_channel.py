from nicos.core import (
    Attach,
    Override,
    Param,
    status,
)
from nicos.devices.abstract import MappedMoveable, MappedReadable, Readable


class PowerSupplyChannel(MappedMoveable):
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

    def doStart(self, value):
        target = self.mapping.get(value, None)
        if target is None:
            raise InvalidValueError(self, f"Position '{value}' not in mapping")
        self._attached_power_control.doStart(value)

    def doStop(self, value):
        target = self.mapping.get(value, None)
        if target is None:
            raise InvalidValueError(self, f"Position '{value}' not in mapping")
        self._attached_power_control.doStart(value)

    def doStatus(self, maxage=0):
        power_stat_msg = self._attached_status.doRead()
        stat, msg = self._attached_voltage.doStatus()
        if stat == status.OK:
            if power_stat_msg == "Power is OFF":
                return status.OK, power_stat_msg
            elif power_stat_msg == "Power is ON":
                return status.BUSY, power_stat_msg
        else:
            return stat, msg

    # def doReset(self):
    #     # Ignore
    #     pass
    #
    # def doReadMapping(self):
    #     return self._attached_power_control.mapping


class PowerSupplyBank(MappedMoveable):
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

    def doStart(self, value):
        target = self.mapping.get(value, None)
        if target is None:
            raise InvalidValueError(self, f"Position '{value}' not in mapping")
        for ps_channel in self._attached_ps_channels:
            ps_channel._attached_power_control.doStart(value)

    def doStop(self, value):
        target = self.mapping.get(value, None)
        if target is None:
            raise InvalidValueError(self, f"Position '{value}' not in mapping")
        for ps_channel in self._attached_ps_channels:
            ps_channel._attached_power_control.doStart(value)

    def doStatus(self, maxage=0):        
        for ps_channel in self._attached_ps_channels:
            stat, msg = ps_channel.doStatus()
            
            if msg == "Power is ON":
                msg = "Module is ON"
                return stat, msg

            if msg != "Power is OFF":
                return stat, msg
            
            if msg == "Power is OFF":
                msg = "Module is OFF"

            return stat, msg
            