import json
import random
from time import time as currenttime

from streaming_data_types.status_x5f2 import deserialise_x5f2
from streaming_data_types.utils import get_schema

from nicos import session
from nicos.core import (
    MASTER,
    POLLER,
    Override,
    Param,
    Readable,
    host,
    listof,
    status,
    tupleof,
)
from nicos.core.constants import SIMULATION
from nicos_ess.devices.kafka.consumer import KafkaSubscriber

DISCONNECTED_STATE = (status.ERROR, "Disconnected")


class KafkaStatusHandler(Readable):
    """Communicates with Kafka and receives status updates, with robust
    reconnect/backoff behavior and debounced idle detection.

    All reconnection logic is handled here; subclasses should *not* try to
    resubscribe themselves. They can still react to status via overriding:

      * _status_update_callback(messages: dict)
      * new_messages_callback(messages)          # called after base parsing
      * no_messages_callback()                   # called when we enter idle
    """

    parameters = {
        "brokers": Param(
            "List of kafka brokers to connect to",
            type=listof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "statustopic": Param(
            "Kafka topic(s) where status messages are written",
            type=listof(str),
            settable=False,
            preinit=True,
            mandatory=True,
            userparam=False,
        ),
        "timeoutinterval": Param(
            "Time to wait (secs) before communication is considered lost",
            type=int,
            default=5,
            settable=True,
            userparam=False,
        ),
        "curstatus": Param(
            "Store the current device status",
            internal=True,
            type=tupleof(int, str),
            settable=True,
        ),
        "statusinterval": Param(
            "Expected time (secs) interval for the status message updates",
            type=int,
            default=2,
            settable=True,
            internal=True,
        ),
        # ---- New tuning knobs (kept modest & overridable in setups) ----
        "reconnect_base_backoff": Param(
            "Initial backoff (s) before attempting resubscribe",
            type=float,
            default=0.5,
            settable=True,
            userparam=False,
        ),
        "reconnect_max_backoff": Param(
            "Maximum backoff (s) between resubscribe attempts",
            type=float,
            default=30.0,
            settable=True,
            userparam=False,
        ),
        "ok_dwell_s": Param(
            "Time (s) of healthy heartbeats before flipping to OK",
            type=float,
            default=2.0,
            settable=True,
            userparam=False,
        ),
        "resub_cooldown_s": Param(
            "Minimum cooldown (s) after a successful resubscribe",
            type=float,
            default=1.0,
            settable=True,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, userparam=False),
    }

    def doPreinit(self, mode):
        # Base backoff init (parameters are available at this point)
        self._next_update = 0.0
        self._kafka_subscriber = None
        self._backoff_s = float(self.reconnect_base_backoff)
        self._next_attempt_ts = 0.0
        self._reconnect_in_flight = False
        self._idle_notified = False
        self._last_msg_ts = currenttime()
        self._ok_after_ts = 0.0

        if session.sessiontype != POLLER and mode != SIMULATION:
            self._kafka_subscriber = KafkaSubscriber(self.brokers)
            # Subscribe using *private* wrappers so base logic always runs.
            self._kafka_subscriber.subscribe(
                self.statustopic,
                messages_callback=self._messages_callback,
                no_messages_callback=self._no_messages_callback,
                error_callback=self._subscriber_error_callback,
            )

        # pessimistic initial state: assume down until heartbeats arrive
        self._next_update = currenttime()
        if self._mode == MASTER:
            self._setROParam("curstatus", (status.WARN, "Trying to connect..."))

    def doRead(self, maxage=0):
        return ""

    def doStatus(self, maxage=0):
        return self.curstatus

    # ----------------- Public (manual) resubscribe -----------------

    def resubscribe(self):
        """Force a resubscription attempt (respects single-flight, but bypasses
        the current cooldown by scheduling 'now')."""
        self._next_attempt_ts = 0.0
        self._maybe_resubscribe(reason="manual")

    # ----------------- Subscriber callback wrappers -----------------

    def _messages_callback(self, messages):
        """Always-called wrapper from KafkaSubscriber: updates liveness,
        resets backoff, manages status hysteresis, then calls the overridable
        new_messages_callback().
        """
        now = currenttime()
        self._last_msg_ts = now

        try:
            # Let subclass/base parse & propagate (includes _set_next_update)
            self.new_messages_callback(messages)
        except Exception as e:
            self.log.warn("Error in new_messages_callback: %s", e)

        # Base behavior that must always run after any valid message(s):
        self._idle_notified = False
        self._reset_backoff()

        if self._mode == MASTER:
            # Step towards healthy. Use WARN first, then flip to OK after dwell.
            cur = getattr(self, "curstatus", None)
            if not cur or cur[0] >= status.WARN:
                # we are coming from WARN/ERROR, show transitional state
                self._setROParam("curstatus", (status.WARN, "Receiving status..."))
                self._ok_after_ts = now + float(self.ok_dwell_s)

            # if we've been healthy for long enough, mark OK
            # we need to make sure that we don't override statuses like "busy"
            if now >= self._ok_after_ts > 0 and cur and cur[1] == "Receiving status...":
                self._setROParam("curstatus", (status.OK, ""))

    def _no_messages_callback(self):
        """Always-called wrapper from KafkaSubscriber on idle polls.
        Debounces idle, sets DISCONNECTED once per idle period, and schedules
        resubscribe attempts with backoff.
        """
        # Only act if master *and* we've truly exceeded our allowed gap.
        if self._mode == MASTER and not self.is_process_running():
            now = currenttime()
            if not self._idle_notified:
                self._idle_notified = True
                self._setROParam("curstatus", DISCONNECTED_STATE)
                self.log.warn(
                    "No status heartbeats; scheduling Kafka resubscribe attempts."
                )
                # give users a hook at the moment we *enter* idle
                try:
                    self.no_messages_callback()
                except Exception as e:
                    self.log.warn("Error in no_messages_callback: %s", e)

            # Try to resubscribe (gated by backoff/single-flight)
            self._maybe_resubscribe(reason="idle")

    # ----------------- Overridable hooks (semantic) -----------------

    def new_messages_callback(self, messages):
        """Default implementation: decode x5f2 messages, update heartbeat window,
        and forward parsed content to _status_update_callback(messages_dict).
        Subclasses may override; base logic above will still handle liveness.
        """
        json_messages = {}
        for timestamp_ms, message in messages:
            try:
                if get_schema(message) != "x5f2":
                    continue
                msg = deserialise_x5f2(message)
                js = json.loads(msg.status_json) if msg.status_json else {}
                js["update_interval"] = msg.update_interval
                json_messages[timestamp_ms] = js
                self._set_next_update(msg.update_interval)
            except Exception as e:
                self.log.warn("Could not decode message from status topic: %s", e)

        if json_messages:
            self._status_update_callback(json_messages)

    def no_messages_callback(self):
        """Hook called *once per idle period* when we transition to DISCONNECTED.
        Subclasses can override to add behavior (logging/metrics/etc.)."""
        # default: nothing beyond the transition done by the wrapper
        return

    # ----------------- Subscriber error path -----------------

    def _subscriber_error_callback(self, err):
        # Surface a human-friendly warning when the poller hits an error
        msg = getattr(err, "str", lambda: str(err))()
        self.log.warn("Kafka subscriber error: %s", msg)
        self._setROParam("curstatus", (status.WARN, f"Kafka subscriber error: {msg}"))
        # Fatal errors should prompt a reconnect attempt; best-effort detection.
        try:
            fatal = getattr(err, "fatal", None)
            is_fatal = fatal() if callable(fatal) else False
        except Exception:
            is_fatal = False
        if is_fatal:
            self._maybe_resubscribe(reason="fatal-error")

    # ----------------- Liveness & timing -----------------

    def is_process_running(self):
        """True if we have not exceeded (expected next update + timeout)."""
        return currenttime() <= (self._next_update + float(self.timeoutinterval))

    def _set_next_update(self, update_interval_ms):
        """Update the 'expected next heartbeat' time using the transmitter's
        advertised interval (ms), stored in statusinterval (s)."""
        update_interval = update_interval_ms // 1000
        if self.statusinterval != update_interval:
            self._setROParam("statusinterval", update_interval)
        next_update = currenttime() + self.statusinterval
        if next_update > self._next_update:
            self._next_update = next_update

    # ----------------- Reconnect/backoff core -----------------

    def _reset_backoff(self):
        self._backoff_s = float(self.reconnect_base_backoff)
        self._next_attempt_ts = 0.0
        self._reconnect_in_flight = False

    def _bump_backoff(self):
        base = max(self._backoff_s, float(self.reconnect_base_backoff))
        cap = float(self.reconnect_max_backoff)
        new_backoff = min(base * 2.0, cap)
        # add jitter up to ±20% of the window
        jitter = random.uniform(-0.2, 0.2) * new_backoff
        self._backoff_s = max(0.1, new_backoff + jitter)
        self._next_attempt_ts = currenttime() + self._backoff_s

    def _maybe_resubscribe(self, reason="unspecified"):
        """Single-flight, backoff-gated resubscribe."""
        if not self._kafka_subscriber:
            return
        now = currenttime()
        if self._reconnect_in_flight or now < self._next_attempt_ts:
            return

        self._reconnect_in_flight = True
        try:
            self._kafka_subscriber.subscribe(
                self.statustopic,
                messages_callback=self._messages_callback,
                no_messages_callback=self._no_messages_callback,
                error_callback=self._subscriber_error_callback,
            )
            # Success: small cooldown; reset idle notification so next heartbeat
            # can move us toward OK.
            self._idle_notified = False
            self._next_attempt_ts = now + float(self.resub_cooldown_s)
            self._setROParam(
                "curstatus",
                (status.WARN, "Kafka subscription restarted; awaiting status..."),
            )
            self.log.info("Kafka resubscribe successful (%s).", reason)
        except Exception as e:
            self._setROParam(
                "curstatus", (status.ERROR, f"Kafka subscription restart failed: {e}")
            )
            self.log.warn("Kafka resubscribe failed (%s): %s", reason, e)
            self._bump_backoff()
        finally:
            self._reconnect_in_flight = False

    # ----------------- Status forwarding -----------------

    def _status_update_callback(self, messages):
        """Called whenever new status messages appear on the status topic.
        Subclasses should override to react to status content.
        :param messages: dict[timestamp_ms] -> parsed JSON
        """

    # ----------------- Shutdown -----------------

    def doShutdown(self):
        if self._kafka_subscriber:
            self._kafka_subscriber.close()
