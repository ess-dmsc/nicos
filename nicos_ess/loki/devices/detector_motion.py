from nicos.core import (
    Override,
    Param,
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

        if ps_bank.doRead() == "ON":
            return False, "Power Supply Bank is still ON (it should be OFF)."
        return True, "Power Supply Bank is OFF. Moving is okay."