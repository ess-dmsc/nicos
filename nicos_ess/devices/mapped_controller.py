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
        "moveable_channels": Attach("Moveable channels", Moveable, multiple=True),
    }

    def doInit(self, mode):
        MappedMoveable.doInit(self, mode)

    def doStart(self, value):

        targets = self.mapping.get(value, None)

        if not isinstance(targets, tuple):
            raise InvalidValueError(self, f"mapping='{value}' is not a tuple")

        if None in targets:
            raise InvalidValueError(self, f"mapping='{value}' contain a None target.")

        if not targets:
            raise InvalidValueError(self, f"mapping='{value}' is empty")

        if len(self._attached_moveable_channels) != len(targets):
            raise InvalidValueError(self, \
                                    "moveable_channels and mapping lengths mismatch.")

        for channel, target in zip(self._attached_moveable_channels, targets):
            channel.doStart(target)

    def doStatus(self, maxage=0):
        return max((channel.doStatus(maxage) for
                channel in self._attached_moveable_channels))

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))

    def doWriteMapping(self, mapping):
        self.valuetype = oneof(*sorted(mapping, key=num_sort))

    def _readRaw(self, maxage=0):
        return tuple(
            channel.read(maxage)
            for channel in self._attached_moveable_channels
        )

    def _mapReadValue(self, value):

        def _abs_diff(tuple1, tuple2):
            return tuple(abs(a - b) for a, b in zip(tuple1, tuple2))

        def _ch_prec_tuple():
            return tuple(channel.precision for channel in 
                        self._attached_moveable_channels)
    
        def _less_than_elementwise(tuple1, tuple2):
            return all(a < b for a, b in zip(tuple1, tuple2))

        for k, v in self.mapping.items():
            if _less_than_elementwise(_abs_diff(v, value), _ch_prec_tuple()):
                return k
        inverse_mapping = {v: k for k, v in self.mapping.items()}
        mapped_value = inverse_mapping.get(value, None)
        if not mapped_value:
            return "In Between"
        return mapped_value
