from nicos.core import Attach, Moveable, Param, multiStatus
from nicos.devices.abstract import TransformedMoveable


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

    def _nanoseconds_to_degrees(self, timedelta):
        return timedelta * self.speed * 360 / 1e9

    def _degrees_to_nanoseconds(self, degrees):
        return degrees * 1e9 / (self.speed * 360)

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
            return self._degrees_to_nanoseconds(target + self.offset)
        except ZeroDivisionError as e:
            raise ValueError("Phase cannot be set when speed is 0") from e

    def _mapReadValue(self, value):
        return self._nanoseconds_to_degrees(value) - self.offset

    def doReadSpeed(self, maxage=0):
        return abs(self._attached_speed_dev.doReadTarget(maxage=maxage))
