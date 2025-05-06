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
            Readable,
        ),
        "power_control": Attach("Control of the power supply channel", MappedMoveable),
    }

    parameter_overrides = {
        "fmtstr": Override(default="%s"),
        "unit": Override(mandatory=False),
        "mapping": Override(
            mandatory=False, settable=False, userparam=False, volatile=True
        ),
    }
    hardware_access = False
    valuetype = str

    def doRead(self, maxage=0):
        return self._attached_voltage.doRead()

    def doStart(self, target):
        if target.lower == "on":
            self._attached_power_control.doStart(target)

    def doStop(self, target):
        if target.lower == "off":
            self._attached_power_control.doStart(target)

    def doStatus(self, maxage=0):
        msg = self._attached_status.doRead()
        if msg.lower() == "no" or msg.lower() == "yes":
            return status.OK, f"Power is ON: {msg}"
        else:
            stat, msg = self._attached_status.doStatus(self, maxage)
            return stat, msg

    def doReset(self):
        # Ignore
        pass

    def doReadMapping(self):
        return self._attached_power_control.mapping
