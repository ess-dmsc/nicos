from nicos import session
from nicos.core import SIMULATION, POLLER
from nicos.devices.abstract import MappedMoveable
from nicos.devices.epics.pva import EpicsMappedMoveable, EpicsDevice


class EpicsShutter(EpicsMappedMoveable):
    """
    May become a general class. Works same as EpicsMappedMoveable, but uses
    choices from the writepv instead of readpv for the mapping.
    """

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
