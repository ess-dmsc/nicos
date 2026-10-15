"""NeXus-enabled simulated cryostat and readbacks of its parameters."""

import random

from nicos.core import LimitError, Param, floatrange, usermethod
from nicos.devices.generic import VirtualRealTemperature
from nicos.devices.generic.paramdev import ReadonlyParamDevice
from nicos_ess.devices.mixins import HasNexusConfig


class SimulatedCryostat(HasNexusConfig, VirtualRealTemperature):
    """Simulated cryostat that can describe itself in the NeXus file."""

    @usermethod
    def jump(self, temperature):
        """Put the cryostat at the temperature at once, without ramping."""
        allowed, why = self.isAllowed(temperature)
        if not allowed:
            raise LimitError(self, why)
        for param in ("target", "setpoint", "regulation", "sample"):
            self._setROParam(param, temperature)


class SimulatedCryostatParameter(HasNexusConfig, ReadonlyParamDevice):
    """Expose a cryostat parameter for scalar logging or a static read."""

    parameters = {
        "jitter": Param(
            "Random noise added to the value", type=floatrange(0), default=0
        ),
    }

    def doRead(self, maxage=0):
        value = ReadonlyParamDevice.doRead(self, maxage)
        if self.jitter:
            value += self.jitter * (0.5 - random.random())
        return value
