from nicos.core import (
    Override,
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
    
    def bank_voltage_is_zero(self, ps_bank):

        if ps_bank is None:
            print("Detector motion: Power supply bank provided for the voltage check is None.")
            return False # Return false to make check fail

        for channel in ps_bank._attached_ps_channels:
            if channel.doReadVoltage_Monitor() > 0:
                print("Detector motion: Some power supply voltages are not zero.")
                return False
        print("Detector motion: Power supply voltages are zero.")
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
        ps_bank = None
        try:
            ps_bank = session.devices[self.ps_bank_name]
        except Exception as e:
            return False, "No Power Supply Bank found in setup ({}).".format(e)

        bank_stat, _ = ps_bank.status()
        bank_on, _ = ps_bank.status_on()
        
        if bank_stat != status.OK:
            return False, "Power Supply Bank is in a NOT OK state."
        if bank_on:
            return False, "Power Supply Bank is still ON (its channels should be OFF)."
        if not self.bank_voltage_is_zero(ps_bank):
            return False, "Power Supply Bank is still ON (its voltages should be zero)."

        print("Detector motion: Power Supply Bank is OFF. Moving is okay.")
        return True, "Power Supply Bank is OFF. Moving is okay."