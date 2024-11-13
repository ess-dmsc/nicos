from collections.abc import Iterable

from nicos.core import Override, Param, Value, oneof, status
from nicos.devices.epics.pva import EpicsReadable
from nicos.devices.generic import CounterChannelMixin, PassiveChannel


class EpicsCounter(CounterChannelMixin, EpicsReadable, PassiveChannel):
    """Counter channel that sums the values of a PV as it changes."""

    parameters = {
        "total": Param(
            "The total amount summed so far", type=float, settable=True, internal=True
        ),
        "started": Param(
            "Whether a collection is in progress",
            type=bool,
            settable=True,
            default=False,
            internal=True,
        ),
    }

    parameter_overrides = {
        # Must run in monitor mode
        "monitor": Override(default=True, settable=False, type=oneof(True)),
        "type": Override(default="counter", settable=False, mandatory=False),
    }

    def value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if self.started:
            value = sum(value) if isinstance(value, Iterable) else value
            self._setROParam("total", self.total + value)

    def doStart(self):
        self.total = 0
        self.started = True

    def doFinish(self):
        self.started = False

    def doStop(self):
        self.started = False

    def doStatus(self, maxage=0):
        if self.started:
            return status.BUSY, "counting"
        return status.OK, ""

    def doRead(self, maxage=0):
        return self.total

    def valueInfo(self):
        return (Value(self.name, unit=self.unit, fmtstr=self.fmtstr),)
