from nicos.core import (
    Param,
)

from nicos_ess.devices.epics.pva import EpicsMappedMoveable

class ConfigurableEpicsMappedMoveable(EpicsMappedMoveable):
    """
    An EpicsMappedMoveable with an extra parameter to allow the ENUM string (key) to be 
    written to PV instead of the index (write_enum_string).

    This class is added for handling some ARINAX EPICS PVs, where the get PV is an ENUM,
    but the set PV is a string.

    TODO: The extra parameter here can, in the future, be incorporated to the original
    EpicsMappedMoveble class.
    """

    parameters = {
        "write_enum_string": Param(
            "Write to PV the enum string instead of the index", type=bool, default=False,
        ),
    }

    def doStart(self, value):
        """ Modified doStart method."""
        if self.write_enum_string:
            self._epics_wrapper.put_pv_value(self.writepv, value)
            return
        super().doStart(value)

