from nicos.core import HasPrecision, oneof
from nicos.utils import num_sort
from nicos_ess.devices.mapped_controller import MappedController


class CenteredSlitMappedController(MappedController):
    """Mapped Controller that accepts width and height as tuple in mapped values."""

    def doInit(self, mode):
        """Override parent doInit to avoid using inverse_mapping which is not used
        and is problematic when tuples become the key.
        """
        self.valuetype = oneof(*sorted(self.mapping, key=num_sort))

    def _mapReadValue(self, value):
        if isinstance(self._attached_controlled_device, HasPrecision):
            for k, v in self.mapping.items():
                if abs(v - value) < self._attached_controlled_device.precision:
                    return k

        if value not in self.mapping.values():
            return "In Between"
        return value
