from nicos.core import (
    Attach,
    Moveable,
    HasPrecision,
    Override,
    InvalidValueError,
    oneof,
)
from nicos.devices.abstract import MappedMoveable
from nicos.utils import num_sort


class MappedController(MappedMoveable):
    parameter_overrides = {
        "mapping": Override(mandatory=True, settable=True, userparam=False),
    }

    attached_devices = {
        "controlled_device": Attach("The attached device", Moveable),
    }

    def doInit(self, mode):
        MappedMoveable.doInit(self, mode)

    def doStart(self, value):
        target = self.mapping.get(value, None)
        if target is None:
            raise InvalidValueError(self, f"Position '{value}' not in mapping")
        self._attached_controlled_device.doStart(target)

    def doStatus(self, maxage=0):
        return self._attached_controlled_device.doStatus(maxage)

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))

    def doWriteMapping(self, mapping):
        self.valuetype = oneof(*sorted(mapping, key=num_sort))

    def _readRaw(self, maxage=0):
        return self._attached_controlled_device.read(maxage)

    def _mapReadValue(self, value):
        if isinstance(self._attached_controlled_device, HasPrecision):
            for k, v in self.mapping.items():
                if abs(v - value) < self._attached_controlled_device.precision:
                    return k
        inverse_mapping = {v: k for k, v in self.mapping.items()}
        mapped_value = inverse_mapping.get(value, None)
        if not mapped_value:
            return "In Between"
        return mapped_value
