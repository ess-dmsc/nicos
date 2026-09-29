import time

from nicos.core import Override, Param, Value, oneof, status
from nicos.devices.generic import CounterChannelMixin, PassiveChannel
from nicos_ess.devices.epics.pva import EpicsReadable
from nicos_ess.devices.epics.pva.epics_common import worst_status


class PulseChargeCounter(CounterChannelMixin, EpicsReadable, PassiveChannel):
    """Counter channel that reads the accumulated charge from EPICS.

    The charge is accumulated in EPICS but this device resets the count to 0
    when a count is started.
    """

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
        "reset_pv": Param(
            "The PV used to reset the counter", type=str, settable=False, internal=True
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
                update.value,
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
        self._publish_state(0)

    def doStart(self):
        self.total = 0
        self.started = True
        self._publish_state(0)
        # Reset the count in the IOC
        self.wrapper.put_pv_value(self.reset_pv, 1, wait=True)

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
        return int(self.total)

    def valueInfo(self):
        return (Value(self.name, unit=self.unit, fmtstr=self.fmtstr),)
