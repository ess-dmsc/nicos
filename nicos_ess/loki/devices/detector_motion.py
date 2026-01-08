from time import sleep

from nicos import session
from nicos.core import (
    Param,
    status,
)
from nicos_ess.devices.epics.pva.motor import EpicsMotor


class LOKIDetectorMotion(EpicsMotor):
    """Control detector bank motion.

    This class restricts movement unless the detector bank's power supply is OFF.
    """

    parameters = {
        "ps_bank_name": Param(
            "Detector bank power supply name in setup",
            type=str,
            mandatory=True,
        ),
        "voltage_off_threshold": Param(
            "The voltage threshold for when the power supply channel is considered off",
            type=float,
            default=0.0,
        ),
    }

    def doInit(self, mode):
        EpicsMotor.doInit(self, mode)
        self._ps_bank = self._get_ps_bank()

    def _get_ps_bank(self):
        ps_bank = session.devices[self.ps_bank_name]
        if not ps_bank:
            self.log.error("Power supply instance does not exist")
        return ps_bank

    def _bank_status_is_ok(self):
        # TODO: Move check to power supply class
        bank_status, status_msg = self._ps_bank.status()
        if bank_status != status.OK:
            self.log.warning(status_msg)
            return False
        return True

    def _bank_is_powered_off(self):
        # TODO: Move check to power supply class
        bank_on, n_channels_on = self._ps_bank.status_on()
        if bank_on:
            self.log.warning("Power supply bank is still ON, all channels must be OFF.")
            return False
        return True

    def _bank_voltage_is_below_threshold(self):
        # TODO: Move check to power supply class
        for channel in self._ps_bank._attached_ps_channels:
            if channel.doReadVoltage_Monitor() > self.voltage_off_threshold:
                self.log.warning(
                    "Power supply bank voltages are above threshold, "
                    "all channels must be less than "
                    f"{self.voltage_off_threshold} {self._ps_bank._get_voltage_unit()}"
                )
                return False
        return True

    def doIsAllowed(self, pos):
        """Hook method from the Device class to check if movement is allowed,
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

        if (
            self._bank_status_is_ok()
            and self._bank_is_powered_off()
            and self._bank_voltage_is_below_threshold()
        ):
            self.log.info(
                "Detector bank motion: Power supply is OFF and voltage is below or equal to threshold. "
                "Movement is permitted."
            )
            return (
                True,
                "Power supply is OFF and voltage is below or equal to threshold.",
            )
        else:
            return False, ""
