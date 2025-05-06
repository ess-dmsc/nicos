from nicos.core import (
    Attach,
    Param,
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

    hardware_access = False
    valuetype = str

    def doRead(self, maxage=0):
        return self._attached_status.doRead()

    def doStart(self, target):
        if target.lower == "on":
            self._attached_power_control.doStart(target)

    def doStop(self, target):
        if target.lower == "off":
            self._attached_power_control.doStart(target)

    def doStatus(self, maxage=0):
        return self._attached_status.doRead()

    def doReset(self):
        # Ignore
        pass

    def doReadMapping(self):
        return self._attached_power_control.mapping
