from enum import Enum

from nicos.core import status, Attach, Param, oneof
from nicos_ess.devices.epics.pva import (
    EpicsMappedMoveable,
    EpicsReadable,
    EpicsStringReadable,
    EpicsDigitalMoveable,
)


class AcqMode(Enum):
    CONTINUOUS = 0
    GATE = 1


class HamaIntensifierController(EpicsMappedMoveable):
    """
    Device that controls the Hamamatsu Intensifier.
    In the future we should also control the gating using the EVR
    """

    parameters = {
        "gain": Param(
            "The gain of the intensifier",
            type=int,
            volatile=True,
            settable=True,
        ),
        "acquisitionmode": Param(
            "The acquisition mode of the intensifier",
            type=oneof("continuous", "gate"),
            volatile=True,
            settable=True,
        ),
    }

    attached_devices = {
        "gain": Attach("The gain of the intensifier", EpicsDigitalMoveable),
        "value": Attach("The current value of the intensifier", EpicsReadable),
        "status": Attach("The status of the intensifier", EpicsStringReadable),
        "connection": Attach(
            "The connection status of the intensifier", EpicsStringReadable
        ),
        "mode": Attach("The operation mode of the intensifier", EpicsMappedMoveable),
    }

    def doStatus(self, maxage=0):
        connection_status = self._attached_connection.read()
        if connection_status != "Connected":
            return status.NOTREACHED, connection_status

        stat, _ = self._attached_status.status(maxage)
        msg = self._attached_status.read(maxage)
        return stat, msg

    def doReadGain(self):
        return self._attached_gain.read()

    def doWriteGain(self, value):
        self._attached_gain.doStart(value)

    def doReadAcquisitionmode(self):
        return AcqMode[self._attached_mode.read().upper()].name.lower()

    def doWriteAcquisitionmode(self, value):
        self._attached_mode.doStart(AcqMode[value.upper()].value)

        if self._attached_mode.read().upper() != value.upper():
            self.log.warning(f"Failed to set acquisition mode to {value}")
            self.log.warning(
                f"Current acquisition mode is {self._attached_mode.read()}"
            )
