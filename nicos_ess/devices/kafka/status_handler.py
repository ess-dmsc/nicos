import json
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
    """Communicates with Kafka and receives status updates.
    The communicator also allows to communicate the status messages
    via callback providing new status messages and their timestamps.
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
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, userparam=False),
    }

    _next_update = 0
    _kafka_subscriber = None

    def doPreinit(self, mode):
        if session.sessiontype != POLLER and mode != SIMULATION:
            self._kafka_subscriber = KafkaSubscriber(self.brokers)
            self._kafka_subscriber.subscribe(
                self.statustopic,
                messages_callback=self.new_messages_callback,
                no_messages_callback=self.no_messages_callback,
                error_callback=self._subscriber_error_callback,
            )

        # Be pessimistic and assume the process is down, if the process
        # is up then the status will be remedied quickly.
        self._next_update = currenttime()

        if self._mode == MASTER:
            self._setROParam("curstatus", (status.WARN, "Trying to connect..."))

    def doRead(self, maxage=0):
        return ""

    def doStatus(self, maxage=0):
        return self.curstatus

    def resubscribe(self):
        """
        Force a resubscription to the Kafka topic(s).
        """
        try:
            self._kafka_subscriber.subscribe(
                self.statustopic,
                self.new_messages_callback,
                self.no_messages_callback,
                error_callback=self._subscriber_error_callback,
            )
            self._setROParam(
                "curstatus",
                (status.WARN, "Kafka subscription restarted; awaiting status..."),
            )
        except Exception as e:
            self._setROParam(
                "curstatus", (status.ERROR, f"Kafka subscription restart failed: {e}")
            )

    def new_messages_callback(self, messages):
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
                self.log.warning("Could not decode message from status topic: %s", e)

        if json_messages:
            self._status_update_callback(json_messages)

    def no_messages_callback(self):
        # Check if the process is still running
        if self._mode == MASTER and not self.is_process_running():
            self._setROParam("curstatus", DISCONNECTED_STATE)

    def _subscriber_error_callback(self, err):
        # Surface a human-friendly warning when the poller hits an error
        msg = getattr(err, "str", lambda: str(err))()
        self.log.warn("Kafka subscriber error: %s", msg)
        self._setROParam("curstatus", (status.WARN, f"Kafka subscriber error: {msg}"))
        # Do not hard ERROR yet; let heartbeats decide. This keeps flapping low.

    def is_process_running(self):
        # Allow some leeway in case of message lag.
        if currenttime() > self._next_update + self.timeoutinterval:
            return False
        return True

    def _status_update_callback(self, messages):
        """This method is called whenever a new status messages appear on
        the status topic. The subclasses should define this method if
        a callback is required when new status messages appear.
        :param messages: dict of timestamp and message in JSON format
        """

    def _set_next_update(self, update_interval):
        update_interval = update_interval // 1000
        if self.statusinterval != update_interval:
            self._setROParam("statusinterval", update_interval)
        next_update = currenttime() + self.statusinterval
        if next_update > self._next_update:
            self._next_update = next_update

    def doShutdown(self):
        self._kafka_subscriber.close()
