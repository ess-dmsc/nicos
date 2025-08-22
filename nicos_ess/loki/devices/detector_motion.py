from time import sleep

from nicos.core import (
    Param,
    status,
)
from nicos_ess.devices.epics.pva.motor import EpicsMotor
from nicos import session


class LOKIDetectorMotion(EpicsMotor):
    """Control detector motion, ensuring power bank safety.

    This class ensures that the detector's power supply bank is OFF
    before allowing any movement.
    """
    
    parameters = {
        "ps_bank_name": Param(
            "Detector power supply bank name in setup",
            type=str,
            mandatory=True,
        ),
    }
    
    def doInit(self, mode):
        EpicsMotor.doInit(self, mode)
        self._ps_bank = self.get_ps_bank()

    def bank_voltage_is_zero(self):
        if self._ps_bank is None:
            print("Power Supply Bank: bank instance provided for the voltage check is NONE.")
            return False # Return false to make check fail

        for channel in self._ps_bank._attached_ps_channels:
            if channel.doReadVoltage_Monitor() > 0:
                return False
        return True

    def doIsAllowed(self, pos):
        """ Hook method from the Device class to check if movement is allowed,
        by verifying if Power Supply Bank is OFF.

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

        if self._ps_bank is None:
            return False, f"Power Supply Bank is None ({self.ps_bank_name})."

        bank_stat, _ = self._ps_bank.status()
        bank_on, _ = self._ps_bank.status_on()
        
        if bank_stat != status.OK:
            return False, "Power Supply Bank is in a NOT OK state."
        if bank_on:
            return False, "Power Supply Bank is still ON (its channels should be OFF)."
        if not self.bank_voltage_is_zero():
            return False, "Power Supply Bank voltages are still > 0 (all voltages should be ZERO)."

        print("Detector motion: Power Supply Bank is OFF and voltages are ZERO. Moving is okay.")
        return True, "Power Supply Bank is OFF. Moving is okay."

    def get_ps_bank(self):
        return session.devices[self.ps_bank_name]
        