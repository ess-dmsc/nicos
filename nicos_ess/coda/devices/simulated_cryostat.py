"""NeXus-enabled readback of a simulated cryostat parameter."""

from nicos.devices.generic.paramdev import ReadonlyParamDevice
from nicos_ess.devices.mixins import HasNexusConfig


class SimulatedCryostatParameter(HasNexusConfig, ReadonlyParamDevice):
    """Expose a numeric cryostat parameter to the NICOS NeXus collector."""
