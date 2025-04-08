import time

from nicos.core import Override, Param, Value, oneof, status
from nicos.devices.generic import CounterChannelMixin, PassiveChannel
from nicos_ess.devices.epics.pva import EpicsReadable
from nicos_ess.devices.epics.pva.epics_devices import get_from_cache_or

# YMIR-TS:Ctrl-EVR-01:EvtACnt-I


class PulseCounter(CounterChannelMixin, EpicsReadable, PassiveChannel):
    """Counter channel that sums the values of a PV as it changes."""

    parameters = {
        "total": Param(
            "The total amount summed so far", type=float, settable=True, internal=True
        ),
        "offset": Param(
            "The offset to be added to the total", type=float, settable=True, default=0
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
        "monitor": Override(default=True, settable=False, type=oneof(True)),
        "type": Override(default="counter", settable=False, mandatory=False),
    }

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self.readpv:
            # Unexpected updates ignored
            return
        time_stamp = time.time()
        self._cache.put(self._name, "unit", units, time_stamp)
        if self.started:
            self._cache.put(self._name, param, value - self.offset, time_stamp)
            self._setROParam("total", value)

    def doStart(self):
        self.total = 0
        self.offset = get_from_cache_or(
            self,
            self._record_fields["readpv"].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self.readpv),
        )
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
        if self.started:
            return int(self.total - self.offset)
        return 0

    def valueInfo(self):
        return (Value(self.name, unit=self.unit, fmtstr=self.fmtstr),)
