from nicos.core import Attach, Moveable, Param, multiStatus
from nicos.devices.abstract import TransformedMoveable


def nanoseconds_to_degrees(timedelta, frequency):
    return timedelta * frequency * 360 / 1e9


def degrees_to_nanoseconds(degrees, frequency):
    return degrees * 1e9 / (frequency * 360)


class ChopperPhase(TransformedMoveable):
    parameters = {
        "speed": Param(
            description="Rotation speed of the chopper in Hz",
            type=float,
            settable=False,
            volatile=True,
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
        "phase_ns_dev": Attach(
            "The attached phase device (ns)", Moveable, optional=False
        ),
        "speed_dev": Attach("The attached speed device (hz)", Moveable, optional=False),
    }

    def _readRaw(self, maxage=0):
        return self._attached_phase_ns_dev.read()

    def _startRaw(self, target):
        self._attached_phase_ns_dev.start(target)

    def doStatus(self, maxage=0):
        return multiStatus(
            (
                ("phase", self._attached_phase_ns_dev),
                ("speed", self._attached_speed_dev),
            ),
            maxage=maxage,
        )

    def _mapTargetValue(self, target):
        try:
            return degrees_to_nanoseconds(target + self.offset, self.speed)
        except ZeroDivisionError as e:
            raise ValueError("Phase cannot be set when speed is 0") from e

    def _mapReadValue(self, value):
        return nanoseconds_to_degrees(value, self.speed) - self.offset

    def doReadSpeed(self, maxage=0):
        return abs(self._attached_speed_dev.read(maxage=maxage))
