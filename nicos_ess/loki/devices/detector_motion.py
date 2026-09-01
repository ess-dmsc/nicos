from nicos.core import (
    Attach,
    Moveable,
    status,
)
from nicos_ess.devices.epics.caen_syx527 import CaenSyx527ChannelGroup
from nicos_ess.devices.epics.pva.motor import EpicsMotor


class LOKIDetectorMotion(EpicsMotor):
    """Control detector bank motion.

    This class restricts movement unless the detector bank's power supply is OFF.
    """

    attached_devices = {
        "power_supply": Attach(
            "Power supply for the detector bank", CaenSyx527ChannelGroup
        ),
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
        return True, ""
