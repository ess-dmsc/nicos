from nicos.core import (
    Attach,
    Moveable,
    HasPrecision,
    Override,
    InvalidValueError,
    oneof,
    Param,
    anytype,
    tupleof,
    status,
)
from nicos.devices.abstract import MappedMoveable
from nicos.utils import num_sort


class MappedController(MappedMoveable):
    parameters = {
        "mappingstatus": Param(
            "Current status that regards the mapping",
            type=tupleof(int, str),
            settable=True,
            default=(status.OK, "idle"),
            no_sim_restore=True,
        ),
    }

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
            message = (
                f"Position '{value}' not in mapping "\
                "and I will not move anything."
            )
            self.mappingstatus = (status.WARN, message)
        else:
            self.mappingstatus = (status.OK, 'idle')
            self._attached_controlled_device.doStart(target)

    def doStatus(self, maxage=0):
        return max(
            self._attached_controlled_device.doStatus(maxage),
            self.mappingstatus
        )

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

    parameters = {
        "mappingstatus": Param(
            "Current status that regards the mapping",
            type=tupleof(int, str),
            settable=True,
            default=(status.OK, "idle"),
            no_sim_restore=True,
        ),
    }

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
        if targets is None:
            message = (
                f"Position '{value}' not in mapping "\
                "and I will not move anything."
            ) 
            self.mappingstatus = (status.WARN, message)
        else:
            self.mappingstatus = (status.OK, 'idle')
            for channel, target in zip(
                    self._attached_controlled_devices, targets):
                channel.doStart(target)

    def doStatus(self, maxage=0):
        devices_status = max(
            (channel.doStatus(maxage) for
                channel in self._attached_controlled_devices),            
        )
        return max(devices_status, self.mappingstatus)

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))

    def doWriteMapping(self, mapping):
        self.valuetype = oneof(*sorted(mapping, key=num_sort))

    def _readRaw(self, maxage=0):
        return tuple(
            channel.read(maxage)
            for channel in self._attached_controlled_devices
        )

    def _mapReadValue(self, value):

        def _abs_diff(tuple1, tuple2):
            return tuple(abs(a - b) for a, b in zip(tuple1, tuple2))

        def _ch_prec_tuple():
            return tuple(channel.precision for channel in
                        self._attached_controlled_devices)

        def _less_than_elementwise(tuple1, tuple2):
            return all(a < b for a, b in zip(tuple1, tuple2))

        def _check_has_precision():
            return all(isinstance(device, HasPrecision)
                       for device in self._attached_controlled_devices)

        if _check_has_precision():
            for k, v in self.mapping.items():
                if _less_than_elementwise(_abs_diff(v, value), _ch_prec_tuple()):
                    return k

        inverse_mapping = {v: k for k, v in self.mapping.items()}
        mapped_value = inverse_mapping.get(value, None)
        if not mapped_value:
            return "In Between"
        return mapped_value

class MultiTargetSelector(MappedController):
    """
    Selector amongst some keys and sends it to MultiTargetComposer
    that can handle several different MultiTargetSelector as channels
    """

    parameters = {
        "mapped_selected_value": Param(
            "Selected value from map (MultiTargetSelector class internal use only)",
            unit="main",
            fmtstr="main",
            type=anytype,
            default=None,
            settable=True
        )
    }

    def doInit(self, mode):
        MappedController.doInit(self, mode)

    def doStart(self, value):
        self.mapped_selected_value = self.mapping.get(value, None)
        self._attached_controlled_device.doStart(value)

    def doRead(self, maxage=0):
        return self.mapped_selected_value

    def doStatus(self, maxage=0):
        return self._attached_controlled_device.doStatus(maxage)

class MultiTargetComposer(Moveable):
    """
    Concatenates strings from a list of MultiTargetSelector
    and sends it to MultiTargetMapping
    """
    
    parameters = {
        "composerstatus": Param(
            "Current status that regards the mapping composer",
            type=tupleof(int, str),
            settable=True,
            default=(status.OK, "idle"),
            no_sim_restore=True,
        ),
    }

    attached_devices = {
        "composition_inputs": Attach("Selector channels", Moveable, multiple=True),
        "composition_output": Attach("Output to MultiTargetMapping", Moveable),
    }

    def doInit(self, mode):
        for input in self._attached_composition_inputs:
            print(input)

    def doStart(self, value):
        full_key=""

        for input in self._attached_composition_inputs:
            individual_key=input.doRead()
            if individual_key is None:
                message = (
                    f"Selector '{input}' is None, "\
                    "perhaps you forgot setting them? "\
                    "I will not move anything."
                )
                self.composerstatus = (status.WARN, message)
                break
            else:
                self.composerstatus = (status.OK, 'idle')
                full_key+=str(individual_key)

        else:
            self._attached_composition_output.doStart(full_key)

    def doRead(self, maxage=0):
        return self._attached_composition_output.doRead(maxage)

    def doStatus(self, maxage=0):
        return max(
            self._attached_composition_output.doStatus(maxage),
            self.composerstatus
        )
