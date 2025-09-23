from nicos.core import Attach, Moveable, Param
from nicos_ess.devices.epics.pva.motor import EpicsMotor


class LokiSampleRotationSpeedConverter(Moveable):
    parameters = {
        "speed": Param(
            description="Rotation speed of the motor in RPM",
            type=float,
            settable=True,
            volatile=True,
            unit="main",
        ),
        "unit": Param(
            description="rpm",
            type=str,
            settable=False,
            volatile=False,
        ),
    }

    attached_devices = {
        "rotation_motor": Attach(
            "The attached sample rotation motor", EpicsMotor, optional=False
        )
    }

    def _convert_degrees_per_second_to_rpm(self, value):
        return (value / 360) * 60

    def _convert_rpm_to_degrees_per_second(self, value):
        return (value / 60) * 360

    def doReadSpeed(self, maxage=0):
        raw_speed = self._attached_rotation_motor.speed
        return self._convert_degrees_per_second_to_rpm(raw_speed)

    def doWriteSpeed(self, target):
        target_raw_speed = self._convert_rpm_to_degrees_per_second(target)
        valid_raw_speed = self._attached_rotation_motor._get_valid_speed(
            target_raw_speed
        )
        valid_speed = self._convert_degrees_per_second_to_rpm(valid_raw_speed)

        if valid_raw_speed != target_raw_speed:
            self.log.warning(
                f"Selected speed {target} {self.unit} is outside the parameter limits, using {round(valid_speed, 3)} {self.unit} instead.",
            )

        self._attached_rotation_motor.speed = valid_raw_speed
        return valid_speed

    def doRead(self, maxage=0):
        return self.doReadSpeed()

    def doStart(self, target):
        self.speed = target
