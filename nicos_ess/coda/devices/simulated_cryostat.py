"""NeXus-enabled simulated cryostat and readbacks of its parameters."""

from nicos.devices.generic import VirtualRealTemperature
from nicos.devices.generic.paramdev import ReadonlyParamDevice
from nicos_ess.devices.mixins import HasNexusConfig


class SimulatedCryostat(HasNexusConfig, VirtualRealTemperature):
    """Simulated cryostat that can describe itself in the NeXus file."""


class SimulatedCryostatParameter(HasNexusConfig, ReadonlyParamDevice):
    """Expose a cryostat parameter for scalar logging or a static read."""
