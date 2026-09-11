from nicos.core import (
    ConfigurationError,
    HasPrecision,
    LimitError,
    oneof,
)
from nicos.utils import num_sort
from nicos_ess.devices.mapped_controller import MappedController


class LokiBeamstopArmPositioner(MappedController):
    def doInit(self, mode):
        MappedController.doInit(self, mode)

    def doWriteMapping(self, mapping):
        if sorted(mapping.keys()) != ["In beam", "Parked"]:
            raise ConfigurationError(
                "Only 'In beam' and 'Parked' are allowed as mapped positions"
            )
        for position in mapping.values():
            self._check_limits(position)
        self.valuetype = oneof(*sorted(mapping, key=num_sort))

    def _mapReadValue(self, value):
        if isinstance(self._attached_controlled_device, HasPrecision):
            for k, v in self.mapping.items():
                if abs(v - value) < self._attached_controlled_device.precision:
                    return k
        inverse_mapping = {v: k for k, v in self.mapping.items()}
        mapped_value = inverse_mapping.get(value)
        if mapped_value:
            return mapped_value
        if value > self.mapping["Parked"]:
            return "Above park position"
        if value < self.mapping["In beam"]:
            return "Below in-beam position"
        return "In between"

    def _check_limits(self, position):
        limits = self._attached_controlled_device.userlimits
        is_allowed, reason = self._attached_controlled_device.isAllowed(position)
        if not is_allowed:
            raise LimitError(
                f"Mapped position ({position}) outside user limits {limits}"
            )
