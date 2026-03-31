"""
This module contains a device for reading the Julabo temperature
controller using EPICS.
"""

from nicos.core import ConfigurationError, HasPrecision, Override, Param, pvname, status
from nicos.devices.epics.mixins import HasDisablePv
from nicos.devices.epics.pva import EpicsAnalogMoveable


class TemperatureController(HasDisablePv, HasPrecision, EpicsAnalogMoveable):
    """
    Julabo devices with status and power switch.

    The device status is obtained via two EPICS PVs, one with an
    integer status code and one with an actual message string.
    Both map directly to the values specified in the device manual
    (for example Julabo F25).

    In addition, the status is WARN when the actuators of the device
    are switched off.
    """

    parameters = {
        "pvprefix": Param("PV prefix for the device", type=str),
        "power": Param(
            "Output power being used",
            type=float,
            settable=False,
            category="general",
            unit="%",
        ),
        "t_external": Param(
            "External PT100 sensor",
            type=float,
            settable=False,
            category="general",
            unit="C",
        ),
        "t_safety": Param(
            "Temperature reported by safety sensor",
            type=float,
            settable=False,
            category="general",
            chatty=True,
            unit="C",
        ),
        "p_internal": Param(
            "Proportional control parameter",
            settable=True,
            type=float,
            category="general",
            chatty=True,
        ),
        "i_internal": Param(
            "Integral control parameter",
            settable=True,
            type=float,
            category="general",
            chatty=True,
        ),
        "d_internal": Param(
            "Derivative control parameter",
            settable=True,
            type=float,
            category="general",
            chatty=True,
        ),
        "p_external": Param(
            "Proportional control parameter",
            settable=True,
            type=float,
            category="general",
            chatty=True,
        ),
        "i_external": Param(
            "Integral control parameter",
            settable=True,
            type=float,
            category="general",
            chatty=True,
        ),
        "d_external": Param(
            "Derivative control parameter",
            settable=True,
            type=float,
            category="general",
            chatty=True,
        ),
    }

    parameter_overrides = {
        "abslimits": Override(mandatory=False),
    }

    @staticmethod
    def _get_record_fields():
        record_fields = {
            "disable_poll": "DisablePoll",
            "disable_ext": "DisableExtSensor",
            "self_tuning": "SelfTuningMode",
            "external_sensor": "ExternalSensor",
            "t_external": "TempExtSensor",
            "t_safety": "TempSafetySensor",
            "setpoint1": "TemperatureSP1",
            "power": "Power",
            "high_limit": "TempHighLimit",
            "low_limit": "TempLowLimit",
            "p_internal": "IntP",
            "i_internal": "IntI",
            "d_internal": "IntD",
            "p_external": "ExtP",
            "i_external": "ExtI",
            "d_external": "ExtD",
            "status_message": "StatusMsg",
            "status_code": "StatusNumber",
        }
        return record_fields

    def doReadTarget(self, maxage=0):
        return self._get_pv("setpoint1")

    def doReadPower(self):
        return self._get_pv("power")

    def doReadT_External(self):
        return self._get_pv("t_external")

    def doReadT_Safety(self):
        return self._get_pv("t_safety")

    def doReadAbslimits(self):
        absmin = self._get_pv("low_limit")
        absmax = self._get_pv("high_limit")
        return absmin, absmax

    def doReadP_Internal(self):
        return self._get_pv("p_internal")

    def doWriteP_Internal(self, target):
        return self._put_pv("p_internal_sp", target)

    def doReadI_Internal(self):
        return self._get_pv("i_internal")

    def doWriteI_Internal(self, target):
        return self._put_pv("i_internal_sp", target)

    def doReadD_Internal(self):
        return self._get_pv("d_internal")

    def doWriteD_Internal(self, target):
        return self._put_pv("d_internal_sp", target)

    def doReadP_External(self):
        return self._get_pv("p_external")

    def doWriteP_External(self, target):
        return self._put_pv("p_external_sp", target)

    def doReadI_External(self):
        return self._get_pv("i_external")

    def doWriteI_External(self, target):
        return self._put_pv("i_external_sp", target)

    def doReadD_External(self):
        return self._get_pv("d_external")

    def doWriteD_External(self, target):
        return self._put_pv("d_external_sp", target)
