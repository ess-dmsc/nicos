from nicos.core import Attach, Override, Param
from nicos.core.mixins import HasLimits
from nicos.devices.abstract import TransformedMoveable
from nicos_ess.devices.epics.pva.motor import EpicsMotor


class MmToDegrees(HasLimits, TransformedMoveable):
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
        "motor": Attach("The attached motor", EpicsMotor, optional=False)
    }

    def doReadAbslimits(self):
        raw_absmin, raw_absmax = self._attached_motor.abslimits
        absmin = self._convert_mm_to_degrees(raw_absmin)
        absmax = self._convert_mm_to_degrees(raw_absmax)
        return absmin, absmax

    def doReadUserlimits(self):
        raw_umin, raw_umax = self._attached_motor.userlimits
        umin = self._convert_mm_to_degrees(raw_umin)
        umax = self._convert_mm_to_degrees(raw_umax)
        return umin, umax

    def doWriteUserlimits(self, value):
        self._attached_motor.userlimits = value
        return self.userlimits

    def isAllowed(self, pos):
        return self._attached_motor.isAllowed(pos)

    def _convert_degrees_to_mm(self, value):
        return value / 0.0845

    def _convert_mm_to_degrees(self, value):
        return value * 0.0845

    def _readRaw(self, maxage=0):
        return self._attached_motor.read()

    def _startRaw(self, target):
        self._attached_motor.start(target)

    def _mapReadValue(self, value):
        return self._convert_mm_to_degrees(value)

    def _mapTargetValue(self, target):
        return self._convert_degrees_to_mm(target)
