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

    def doStart(self, target):
        print("PS doStart target.lower() = " + str(target.lower()))
        if target.lower() == "on":
            print("PS calling _attached_power_control.doStart")
            self._attached_power_control.doStart(target.lower())

    def doStop(self, target):
        if target.lower == "off":
            self._attached_power_control.doStart(target.lower())

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
