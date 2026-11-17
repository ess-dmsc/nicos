import time

from nicos import session
from nicos.core import POLLER, SIMULATION, Override, Param, Value, oneof, status
from nicos.devices.generic import CounterChannelMixin, PassiveChannel
from nicos_ess.devices.epics.pva import EpicsReadable
from nicos_ess.devices.epics.pva.epics_common import worst_status

FINAL_UPDATE_TIMEOUT = 2.0
FINAL_UPDATE_POLL_INTERVAL = 0.02


class PulseChargeCounter(CounterChannelMixin, EpicsReadable, PassiveChannel):
    """Counter channel for reading the acculumulated charge current from EPICS."""

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
        if self._ignore_next_update:
            self._ignore_next_update = False
        # If the beam is off we can get random noise which could
        # be negative (though very small).
        elif update.value > 0:
            total = self.total + update.value
            self._cache.put(self._name, "total", total, time_stamp)
        self._refresh_status(time_stamp)

    def _on_connection_change(self, change):
        # the monitor sends the current value again on reconnect
        if change.is_connected:
            self._ignore_next_update = True
        super()._on_connection_change(change)

    def doPreinit(self, mode):
        super().doPreinit(mode)
        self._ignore_next_update = False
        self._started_at = self._stopped_at = float("inf")
        self._total_at_start = self._total_at_stop = 0.0
        self._stop_passed = False

    def _after_subscribe(self, mode):
        super()._after_subscribe(mode)
        if mode != SIMULATION and session.sessiontype != POLLER:
            self._total_at_start = self._total_at_stop = self.total
            self._cache.addCallback(self, "total", self._on_total_update)

    def doShutdown(self):
        if self._cache and session.sessiontype != POLLER:
            self._cache.removeCallback(self, "total", self._on_total_update)
        super().doShutdown()

    def _on_total_update(self, key, total, time_stamp, *args):
        if time_stamp <= self._started_at:
            self._total_at_start = total
        if time_stamp <= self._stopped_at:
            self._total_at_stop = total
            if time_stamp > self._started_at:
                self._cache.put(self._name, "value", self.doRead(), time_stamp)
        else:
            self._stop_passed = True

    def _publish_state(self, value=Ellipsis):
        timestamp = time.time()
        if value is not Ellipsis:
            self._cache.put(self._name, "value", value, timestamp)
        self._refresh_status(timestamp)

    def doPrepare(self):
        self._started_at = self._stopped_at = float("inf")
        self._total_at_start = self._total_at_stop = self.total
        self._stop_passed = False
        self._publish_state(0)

    def doStart(self):
        self.started = True
        self._started_at = time.time()
        self._publish_state(0)

    def doFinish(self):
        self.started = False
        self._stopped_at = time.time()
        waited = 0.0
        while not self._stop_passed and waited < FINAL_UPDATE_TIMEOUT:
            session.delay(FINAL_UPDATE_POLL_INTERVAL)
            waited += FINAL_UPDATE_POLL_INTERVAL
        self._publish_state(self.doRead())

    def doStop(self):
        self.started = False
        self._stopped_at = time.time()
        self._publish_state(self.doRead())

    def _compute_status(self, maxage=0):
        counter_status = (status.BUSY, "counting") if self.started else (status.OK, "")
        return worst_status(super()._compute_status(maxage), counter_status)

    def doRead(self, maxage=0):
        return self._total_at_stop - self._total_at_start

    def valueInfo(self):
        return (Value(self.name, unit=self.unit, fmtstr=self.fmtstr),)
