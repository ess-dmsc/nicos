from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Param,
    none_or,
    pvname,
)
from nicos.devices.abstract import MappedMoveable
from nicos.devices.epics.pva import (
    EpicsDevice,
    EpicsMappedMoveable,
    EpicsMappedReadable,
)


class EpicsShutter(EpicsMappedMoveable):
    """
    May become a general class. Works same as EpicsMappedMoveable, but uses
    choices from the writepv instead of readpv for the mapping.
    """

    parameters = {
        "resetpv": Param(
            "PV for resetting device",
            type=none_or(pvname),
            mandatory=False,
            userparam=False,
        ),
    }

    def _get_pv_parameters(self):
        pv_parameters = super()._get_pv_parameters()
        return pv_parameters | {"resetpv"} if self.resetpv else pv_parameters

    def doInit(self, mode):
        if mode == SIMULATION:
            return

        EpicsDevice.doInit(self, mode)

        if session.sessiontype != POLLER:
            choices = self._epics_wrapper.get_value_choices(
                self._get_pv_name("writepv")
            )
            # Create mapping from EPICS information
            new_mapping = {}
            for i, choice in enumerate(choices):
                new_mapping[choice] = i
            self._setROParam("mapping", new_mapping)
        MappedMoveable.doInit(self, mode)

    def doReset(self):
        """Reset shutter state by writing on the configured 'resetpv' parameter"""

        if self.resetpv:
            self._put_pv("resetpv", True)
        else:
            self.log.warn("Reset isn't available on device or the resetpv is missing")


class EpicsHeavyShutter(EpicsMappedReadable):
    """
    Readable class for heavy shutters with optional reset capabilities
    """

    parameters = {
        "resetpv": Param(
            "PV for resetting device",
            type=none_or(pvname),
            mandatory=False,
            userparam=False,
        ),
    }

    def _get_pv_parameters(self):
        return {"readpv"} | {"resetpv"} if self.resetpv else {"readpv"}

    def doReset(self):
        """Reset shutter state by writing on the configured 'resetpv' parameter"""

        if self.resetpv:
            self._put_pv("resetpv", True)
        else:
            self.log.warn("Reset isn't available on device or the resetpv is missing")
