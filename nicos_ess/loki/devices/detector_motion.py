from time import sleep

from nicos.core import (
    Override,
    Param,
    status,
)
from nicos.core.utils import (
    usermethod,
)
from nicos_ess.devices.epics.pva.motor import EpicsMotor
from nicos import session

WAIT = 3
MAX_RETRIES = 10


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
            return False, "No Power Supply Bank is None ({}).".format(e)

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
    
    def _enable_ps_bank(self, on):
        for channel in self._ps_bank._attached_ps_channels:
            channel.enable() if on else channel.disable()

    def enable_ps_bank(self):
        self._enable_ps_bank(True)

    def disable_ps_bank(self):
        self._enable_ps_bank(False)
    
    def get_ps_bank(self):
        return session.devices[self.ps_bank_name]
    
    def _check_start(self, pos):
        """ Overwrite super method.

        Note: As start() can't be overwritten, _check_start had to be
        customized in order to add the disable_ps_bank() step before
        movement can be issued."""

        self._ps_bank = self.get_ps_bank()

        print(f"Detector motion: Disabling {self.ps_bank_name}...")
        self.disable_ps_bank()
        sleep(WAIT) # Wait for disable to be complete.

        # Check if bank is off before checking the voltage.
        bank_on, _ = self._ps_bank.status_on()
        if bank_on:
            return Ellipsis # Fail check.

        # Wait for voltage to be 0, it may take a while.
        print(f"Detector motion: Waiting {self.ps_bank_name} voltages to be zero...")
        for retry in range(MAX_RETRIES):
            if self.bank_voltage_is_zero():
                break # Success
            sleep(WAIT)
            
            if retry == MAX_RETRIES - 1:
                print(f"Detector motion: Reached maximum number of retries for voltage check.")

        return super()._check_start(pos)
    
    def doStart(self, target):
        """ Perfome movement as per usual, and after this enable PS Bank. """

        super().doStart(target)
        print(f"Detector motion: Enabling {self.ps_bank_name}...")
        self.enable_ps_bank()
        # Add check of status on, with some retries.

