from nicos.core import Attach, HasLimits, Moveable, Override, Param, multiStatus
from nicos.devices.abstract import TransformedMoveable
from nicos_ess.devices.epics.pva import EpicsManualMappedAnalogMoveable
from nicos_ess.devices.epics.pva.motor import EpicsJogMotor


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
        "mapped_speed_dev": Attach(
            "The attached speed device (hz)",
            EpicsManualMappedAnalogMoveable,
        ),
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
                ("speed", self._attached_mapped_speed_dev),
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
        target_val = self._attached_mapped_speed_dev.doReadTarget(maxage=maxage)
        return abs(self._attached_mapped_speed_dev.mapping.get(target_val))


class DegreesPerSecondToRPM(HasLimits, TransformedMoveable):
    parameters = {
        "unit": Param(
            description="Converts unit of attached motor from degrees/sec to RPM",
            type=str,
            settable=False,
            default="rpm",
        )
    }

    parameter_overrides = {
        "abslimits": Override(volatile=True, mandatory=False),
        "userlimits": Override(volatile=True, chatty=False),
    }

    attached_devices = {
        "motor": Attach("The attached motor", EpicsJogMotor, optional=False)
    }

    def doReadAbslimits(self):
        raw_absmin, raw_absmax = self._attached_motor.abslimits
        absmin = self._convert_degrees_per_second_to_rpm(raw_absmin)
        absmax = self._convert_degrees_per_second_to_rpm(raw_absmax)
        return absmin, absmax

    def doReadUserlimits(self):
        raw_umin, raw_umax = self._attached_motor.userlimits
        umin = self._convert_degrees_per_second_to_rpm(raw_umin)
        umax = self._convert_degrees_per_second_to_rpm(raw_umax)
        return umin, umax

    def doWriteUserlimits(self, value):
        self._attached_motor.userlimits = value
        return self.userlimits

    def _convert_degrees_per_second_to_rpm(self, value):
        return (value / 360) * 60

    def _convert_rpm_to_degrees_per_second(self, value):
        return (value / 60) * 360

    def _readRaw(self, maxage=0):
        return self._attached_motor.read()

    def _startRaw(self, target):
        self._attached_motor.start(target)

    def _mapReadValue(self, value):
        return self._convert_degrees_per_second_to_rpm(value)

    def _mapTargetValue(self, target):
        return self._convert_rpm_to_degrees_per_second(target)
