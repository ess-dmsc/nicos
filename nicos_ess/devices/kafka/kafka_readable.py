from streaming_data_types import deserialise_f144
from streaming_data_types.utils import get_schema

from nicos import session
from nicos.core import (
    Readable,
    Param,
    listof,
    host,
    tupleof,
    POLLER,
    SIMULATION,
    MASTER,
    status,
)
from nicos_ess.devices.kafka.consumer import KafkaSubscriber


class F144Readable(Readable):
    parameters = {
        "brokers": Param(
            "List of kafka brokers to connect to",
            type=listof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "topic": Param(
            "Kafka topic(s) where messages are written",
            type=listof(str),
            settable=False,
            preinit=True,
            mandatory=True,
            userparam=False,
        ),
        "source_name": Param(
            "Name of the source to filter messages",
            type=str,
            settable=True,
            mandatory=True,
        ),
        "curstatus": Param(
            "Store the current device status",
            internal=True,
            type=tupleof(int, str),
            settable=True,
        ),
        "curvalue": Param(
            "Store the current value",
            internal=True,
            settable=True,
            unit="main",
        ),
    }

    _kafka_subscriber = None

    def doPreinit(self, mode):
        if session.sessiontype != POLLER and mode != SIMULATION:
            self._kafka_subscriber = KafkaSubscriber(self.brokers)
            self._kafka_subscriber.subscribe(
                self.topic,
                self.new_messages_callback,
                self.no_messages_callback,
            )

        if self._mode == MASTER:
            self._setROParam("curstatus", (status.WARN, "Trying to connect..."))

    def doRead(self, maxage=0):
        return self.curvalue

    def doStatus(self, maxage=0):
        return self.curstatus

    def new_messages_callback(self, messages):
        for timestamp, message in messages:
            try:
                if get_schema(message) != "f144":
                    continue
                msg = deserialise_f144(message)

                if msg.source_name != self.source_name:
                    continue

                self._setROParam("curvalue", msg.value)
                self._setROParam("curstatus", (status.OK, ""))

            except Exception as e:
                self.log.warning("Could not decode message from topic: %s", e)
                self._setROParam(
                    "curstatus", (status.ERROR, "Could not decode message")
                )

    def no_messages_callback(self):
        pass

    def doShutdown(self):
        self._kafka_subscriber.close()
