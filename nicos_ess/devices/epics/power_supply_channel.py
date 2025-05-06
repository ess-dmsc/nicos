from nicos.core import (
    Attach,
    Param,
)
from nicos.devices.abstract import MappedMoveable
from nicos_ess.devices.epics.pva import (
    EpicsMappedMoveable,
    EpicsMappedReadable,
    EpicsReadable,
)
from nicos_ess.devices.epics.pva.epics_devices import EpicsParameters


class PowerSupplyChannel(EpicsParameters, MappedMoveable):
    parameters = {
        "board": Param("Power supply board"),
        "channel": Param("Power supply channel"),
    }
    attached_devices = {
        "voltage": Attach("Monitored voltage", EpicsReadable),
        "current": Attach("Monitored current", EpicsReadable),
        "status": Attach(
            "Status of the power in the power supply channel",
            EpicsMappedReadable,
        ),
        "power_control": Attach(
            "Control of the power supply channel", EpicsMappedMoveable
        ),
    }

    hardware_access = False
    valuetype = str

    def __init__(self, name, **config):
        super().__init__(name, config)
        self._attached_status = None
        self._attached_power_control = None

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
