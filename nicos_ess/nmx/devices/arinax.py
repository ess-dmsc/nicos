from nicos.core import (
    Param,
    HasPrecision,
    HasLimits,
    anytype,
    SIMULATION
)

from nicos.devices.epics.pva import EpicsDevice, EpicsMoveable

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


class EpicsArinaxMoveable(EpicsMoveable):
    """
    Handles EPICS Arinax devices (such as actuators/motors) which 
    have getter and setter of different types.
    
    E.g., for Phi, Chi and Theta ARINAX actuators, the getter PV is float, 
    but setter is string.
    """

    valuetype = anytype

    def doInit(self, mode):
        """Modified doInit method. Skips in/outtype checks."""

        if mode == SIMULATION:
            return
            
        EpicsDevice.doInit(self, mode)
    
    def doStart(self, value):
        out_type = self._epics_wrapper.get_pv_type(self._param_to_pv["writepv"]) # TODO: Move it to a better place.
        value = out_type(value) # Converts to out type.
        self._put_pv("writepv", value)