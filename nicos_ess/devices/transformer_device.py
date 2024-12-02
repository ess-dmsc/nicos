from nicos.core import Attach, Moveable, Param, ProgrammingError
from nicos.devices.abstract import TransformedMoveable


def nanoseconds_to_degrees(timedelta, frequency):
    return timedelta * frequency * 360 / 1e9


def degrees_to_nanoseconds(degrees, frequency):
    return degrees * 1e9 / (frequency * 360)


class TransformedAttachedMoveable(TransformedMoveable):
    parameters = {
        "speed": Param(
            description="Rotation speed of the chopper in Hz",
            default=14,
            type=float,
            settable=True,
            mandatory=True,
        ),
        "offset": Param(
            description="Offset of the chopper in degrees",
            default=0,
            type=float,
            settable=True,
            mandatory=True,
        ),
    }

    attached_devices = {
        "raw_device": Attach("The attached devices", Moveable, optional=False)
    }

    def _mapReadValue(self, value):
        raise ProgrammingError(
            self, "Somebody please implement a proper " "_mapReadValue method!"
        )

    def _readRaw(self, maxage=0):
        return self._attached_raw_device.read()

    def _mapTargetValue(self, target):
        raise ProgrammingError(
            self, "Somebody please implement a proper " "_mapTargetValue method!"
        )

    def _startRaw(self, target):
        self._attached_raw_device.start(target)

    def doStatus(self, maxage=0):
        return self._attached_raw_device.status(maxage=maxage)


class ChopperPhase(TransformedAttachedMoveable):
    parameters = {
        "speed": Param(
            description="Rotation speed of the chopper in Hz",
            default=14,
            type=float,
            settable=True,
            mandatory=True,
        ),
        "offset": Param(
            description="Offset of the chopper in degrees",
            default=0,
            type=float,
            settable=True,
            mandatory=True,
        ),
    }

    def _mapReadValue(self, value):
        return nanoseconds_to_degrees(value, self.speed) - self.offset

    def _mapTargetValue(self, target):
        return degrees_to_nanoseconds(target + self.offset, self.speed)
