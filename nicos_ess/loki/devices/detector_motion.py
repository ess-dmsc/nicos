from nicos.core import (
    Attach,
    Param,
    status,
)
from nicos_ess.devices.epics.power_supply_channel import PowerSupplyBank
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
        "power_supply": Attach("Power supply for detector bank 0", PowerSupplyBank),
    }

    def _bank_status_is_ok(self):
        # # TODO: Move check to power supply class
        bank_status, status_msg = self._attached_power_supply.status()
        status_ok = bank_status == status.OK
        return status_ok, status_msg

    def _bank_is_powered_off(self):
        # TODO: Move check to power supply class
        bank_on, n_channels_on = self._attached_power_supply.status_on()
        if bank_on:
            return False, "Power supply bank is still ON, all channels must be OFF."
        return True, ""

    def _bank_voltage_is_below_threshold(self):
        # TODO: Move check to power supply class
        volt_unit = f"{self._attached_power_supply._get_voltage_unit()}"
        error_msg = (
            "Power supply bank voltages are above threshold, "
            "all channels must be less than "
            f"{self.voltage_off_threshold} {volt_unit}"
        )
        for channel in self._attached_power_supply._attached_ps_channels:
            if channel.doReadVoltage_Monitor() > self.voltage_off_threshold:
                return False, error_msg
        return True, ""

    def isAllowed(self, pos):
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

        status_ok, msg = self._bank_status_is_ok()
        if not status_ok:
            return False, msg

        power_off, msg = self._bank_is_powered_off()
        if not power_off:
            return False, msg

        voltage_below_thresh, msg = self._bank_voltage_is_below_threshold()
        if not voltage_below_thresh:
            return False, msg

        return EpicsMotor.isAllowed(self, pos)
