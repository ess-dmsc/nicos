from nicos.core import (
    Override,
    Param,
)
from nicos_ess.devices.epics.pva.motor import EpicsMotor
from nicos import session

class LOKIDetectorMotion(EpicsMotor):
    """
    Device that controls the detector motion, with a check for the 
    detector power supply bank before movement is attempted.

    The detector power supply bank must be OFF before any movement is done.
    """
    parameters = {
        "ps_bank_name": Param(
            "Detector power supply bank name in setup",
            type=str,
            mandatory=True,
        ),
    }

    def is_ps_bank_off(self):
        """ Checks if Power Supply Bank is OFF."""
        ps_bank = None
        try:
            ps_bank = session.devices[self.ps_bank_name]
        except Exception as e:
            print("Detector motion: " + str(e))
            print("Detector motion: no Power Supply Bank found in setup. Not moving.")
            return False

        if ps_bank.doRead() == "ON":
            print("Detector motion: Power Supply Bank is ON (it should be OFF). Not moving.")
            return False
        print("Detector motion: Power Supply Bank is OFF. Moving is okay.")
        return True
    
    def _check_start(self, pos):
        """ Overwrites super method."""
        if not self.is_ps_bank_off():
            return Ellipsis
        return super()._check_start(pos)