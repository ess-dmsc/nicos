from nicos.core import (
    Attach,
    Moveable,
    Param,
    status,
)
from nicos_ess.devices.epics.power_supply_group import PowerSupplyGroup
from nicos_ess.devices.epics.pva.motor import EpicsMotor


class LOKIDetectorMotion(EpicsMotor):
    """Control detector bank motion.

    This class restricts movement unless the detector bank's power supply is OFF.
    """

    parameters = {
        "voltage_off_threshold": Param(
            "The voltage threshold for when the power supply channel is considered off",
            type=float,
            default=0.0,
        ),
    }

    attached_devices = {
        "power_supply": Attach("Power supply for the detector bank", PowerSupplyGroup),
    }

    def isAllowed(self, pos):
        return Moveable.isAllowed(self, pos)

    def doIsAllowed(self, pos):
        """
        Hook method from the Device class to check if movement is allowed,
        by verifying if power supply is OFF.

        Parameters
        ----------
        pos : any
            Target position (not used).

        Returns
        -------
        ok : bool
            True if movement is permitted, False otherwise.
        why : str
            Message indicating why movement is or isn't allowed.
        """

        power_status, message = self._attached_power_supply.status()
        if power_status != status.DISABLED:
            return False, message

        voltages = self._attached_power_supply.read()
        if not isinstance(voltages, tuple):
            voltages = (voltages,)
        maximum = max(abs(voltage) for voltage in voltages)
        if maximum > self.voltage_off_threshold:
            return (
                False,
                f"power-supply voltage is still {maximum:g} "
                f"{self._attached_power_supply.unit}; it must be at most "
                f"{self.voltage_off_threshold:g} {self._attached_power_supply.unit}",
            )
        return True, ""
