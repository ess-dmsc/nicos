import time
from dataclasses import replace

from nicos.core import (
    Override,
    Param,
    PositionError,
    anytype,
    nonemptylistof,
    oneof,
    pvname,
)
from nicos.devices.abstract import Moveable
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsChannelInfo,
    EpicsChannelRole,
    EpicsDeviceBase,
)


class ManualSwitch(EpicsDeviceBase, Moveable):
    """A manually change-able, discrete-state EPICS device."""

    parameters = {
        "writepv": Param(
            "PV that stores the chosen state",
            type=pvname,
            mandatory=True,
            userparam=False,
        ),
        "states": Param(
            "List of allowed logical states",
            type=nonemptylistof(anytype),
            mandatory=True,
        ),
        "mapping": Param(
            "Dict mapping logical *states* → raw PV values",
            type=dict,
            mandatory=False,
            settable=False,
            default={},
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False),
    }

    _primary_channel = "write"
    _epics_channels = {
        "write": EpicsChannelInfo(
            "target", "", EpicsChannelRole.VALUE_AND_STATUS, pv_attr="writepv"
        ),
    }

    def doPreinit(self, mode):
        if not self.mapping:
            self.mapping = {state: state for state in self.states}
        self._reverse_mapping = {v: k for k, v in self.mapping.items()}
        EpicsDeviceBase.doPreinit(self, mode)

    def _after_subscribe(self, mode):
        self.valuetype = oneof(*self.states)

    def doStart(self, target):
        if target not in self.states:
            raise PositionError(self, f"{target!r} is not among {self.states!r}")

        self._epics.put_channel_value("write", self.mapping[target])
        self._cache.put(self._name, "target", target, time.time())

    def doReadTarget(self):
        raw = self._read_channel_cached("write")
        return self._reverse_mapping.get(raw, raw)

    def doRead(self, maxage=0):
        return (
            self.target
            if self.target in self.states
            else f"Unknown target {self.target!r} not in {self.states!r}"
        )

    def doIsAllowed(self, target):
        ok = target in self.states
        return ok, "" if ok else f"{target!r} is not in {self.states!r}"

    def _on_channel_update(self, update):
        value = self._reverse_mapping.get(update.value, update.value)
        super()._on_channel_update(replace(update, value=value))
