from nicos.core import (
    Attach,
    HasPrecision,
    InvalidValueError,
    Moveable,
    Override,
    Param,
    PositionError,
    Readable,
    multiStatus,
    oneof,
    status,
)
from nicos.core.utils import multiWait
from nicos.devices.abstract import (
    MappedMoveable,
)
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

    def doIsAllowed(self, key):
        why = []
        target = self.mapping.get(key, None)
        if target is None:
            why.append(f"Position '{key}' not in mapping")
        else:
            dev = self._attached_controlled_device
            ok, _why = dev.isAllowed(target)
            if ok:
                self.log.debug(f"{dev}: requested target {target} allowed.")
            else:
                why.append(f"{dev}: requested target {target} Not allowed; {_why}")

        if why:
            return False, why
        return True, ""

    def doStart(self, value):
        target = self.mapping.get(value, None)
        self._attached_controlled_device.start(target)

    def doStatus(self, maxage=0):
        return self._attached_controlled_device.status(maxage)

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


class MultiTargetMapping(MappedMoveable):
    """
    Class for devices that map one key to a set (tuple) of values

    Pratically same as `MappedController` class but maps to a tuple
    instead of a single value.

    TODO: refactor this class to somehow allow single values too, as
    `MappedController` does. I tried implementing it by formatting
    the inputs from float, int to tuple but then the values on the left
    corner of GUI appeared as 'In Between' for a new value added manually
    by the user.
    """

    parameter_overrides = {
        "mapping": Override(mandatory=True, settable=True, userparam=False),
    }

    attached_devices = {
        "controlled_devices": Attach("Moveable channels", Moveable, multiple=True),
    }

    def doInit(self, mode):
        MappedMoveable.doInit(self, mode)

    def doStart(self, value):
        targets = self.mapping.get(value, None)
        for channel, target in zip(self._attached_controlled_devices, targets):
            channel.doStart(target)

    def doStatus(self, maxage=0):
        if self._adevs:
            return multiStatus(self._adevs, maxage)
        return (status.UNKNOWN, "doStatus not implemented")

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))

    def doWriteMapping(self, mapping):
        self.valuetype = oneof(*sorted(mapping, key=num_sort))

    def _readRaw(self, maxage=0):
        return tuple(
            channel.read(maxage) for channel in self._attached_controlled_devices
        )

    def _mapReadValue(self, value):
        def _abs_diff(tuple1, tuple2):
            return tuple(abs(a - b) for a, b in zip(tuple1, tuple2))

        def _ch_prec_tuple():
            return tuple(
                channel.precision for channel in self._attached_controlled_devices
            )

        def _less_than_elementwise(tuple1, tuple2):
            return all(a < b for a, b in zip(tuple1, tuple2))

        def _check_has_precision():
            return all(
                isinstance(device, HasPrecision)
                for device in self._attached_controlled_devices
            )

        if _check_has_precision():
            for k, v in self.mapping.items():
                if _less_than_elementwise(_abs_diff(v, value), _ch_prec_tuple()):
                    return k

        inverse_mapping = {v: k for k, v in self.mapping.items()}
        mapped_value = inverse_mapping.get(value, None)
        if not mapped_value:
            return "In Between"
        return mapped_value


class MultiTargetSelector(MappedMoveable):
    """
    Select amongst a dict of values to be used for the composer,
    together with more selectors, to assembly a key
    """

    parameters = {
        "idx": Param(
            "Index that this selector will write on the final string",
            type=int,
            mandatory=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False),
    }

    attached_devices = {
        "composer": Attach("Selector channels", Moveable, optional=False),
    }

    parameter_overrides = {
        "mapping": Override(mandatory=True, settable=True, userparam=False),
    }

    def doInit(self, mode):
        self._attached_composer.register_selector(self)
        self._internal_val = None
        MappedMoveable.doInit(self, mode)

    def doStart(self, value):
        self._internal_val = self.mapping.get(value)
        self._attached_composer.start(self.mapping.get(value))

    def doStatus(self, maxage=0):
        return self._attached_composer.status(maxage)

    def _readRaw(self, maxage=0):
        mapped_val_str = self._attached_composer.read(maxage)
        if mapped_val_str == "In Between":
            return mapped_val_str
        mapped_val_list = mapped_val_str.split(",")
        return mapped_val_list[self.idx]

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))

    def _mapReadValue(self, target):
        try:
            return MappedMoveable._mapReadValue(self, target)
        except PositionError:
            return target

    def get_idx(self):
        return self.idx

    def get_internal_val(self):
        return self._internal_val


class MultiTargetComposer(Moveable, Readable):
    """
    Concatenates strings from MultiTargetSelector
    and sends it to MultiTargetMapping
    """

    parameter_overrides = {
        "unit": Override(mandatory=False),
    }

    attached_devices = {
        "out": Attach("Selector channels", MappedMoveable),
    }

    def doInit(self, mode):
        self._selectors = []

    def register_selector(self, selector_object):
        self._selectors.append(selector_object)

    def doStart(self, value):
        out_tgt = [None] * len(self._selectors)
        for selector in self._selectors:
            val = selector.get_internal_val()
            if not val:
                raise InvalidValueError(f"Perhaps you need to set {selector}?")
            idx = selector.get_idx()
            out_tgt[idx] = val
        out = self._attached_out
        out.start(",".join(out_tgt))

    def doRead(self, maxage=0):
        return self._attached_out.read(maxage)

    def doStatus(self, maxage=0):
        return self._attached_out.status(maxage)
