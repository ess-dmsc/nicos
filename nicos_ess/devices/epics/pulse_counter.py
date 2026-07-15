import time

from nicos.core import Override, Param, Value, oneof, status
from nicos.devices.generic import CounterChannelMixin, PassiveChannel
from nicos_ess.devices.epics.pva import EpicsReadable
from nicos_ess.devices.epics.pva.epics_common import worst_status


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

    def _on_channel_update(self, update):
        if update.channel != "read":
            return
        time_stamp = time.time()
        self._cache.put(self._name, "unit", update.units, time_stamp)
        self._cache.put(
            self._name,
            "value_status",
            (update.severity, update.message),
            time_stamp,
        )
        self._log_alarm_once(update.channel, update.severity, update.message)
        if self.started:
            self._cache.put(
                self._name,
                self._epics.cache_key_for(update.channel),
                update.value - self.offset,
                time_stamp,
            )
            self._setROParam("total", update.value)
        self._refresh_status(time_stamp)

    def _publish_state(self, value=Ellipsis):
        timestamp = time.time()
        if value is not Ellipsis:
            self._cache.put(self._name, "value", value, timestamp)
        self._refresh_status(timestamp)

    def doPrepare(self):
        self.total = 0
        self.offset = 0
        self._publish_state(0)

    def doStart(self):
        self.offset = self._epics.get_channel_value("read")
        self.total = self.offset
        self.started = True
        self._publish_state(0)

    def doFinish(self):
        self.started = False
        self._publish_state()

    def doStop(self):
        self.started = False
        self._publish_state()

    def _compute_status(self, maxage=0):
        counter_status = (status.BUSY, "counting") if self.started else (status.OK, "")
        return worst_status(super()._compute_status(maxage), counter_status)

    def doRead(self, maxage=0):
        return int(self.total - self.offset)

    def valueInfo(self):
        return (Value(self.name, unit=self.unit, fmtstr=self.fmtstr),)
