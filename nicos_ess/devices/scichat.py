import json

from nicos import session
from nicos.core import Device, Param, host, listof, usermethod
from nicos.core.constants import SIMULATION
from nicos_ess.devices.kafka.producer import KafkaProducer


class ScichatBot(Device):
    """A device for sending messages to SciChat via Kafka."""

    parameters = {
        "brokers": Param(
            "List of kafka hosts to use",
            type=listof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "scichat_topic": Param(
            "Kafka topic where Scichat messages are sent",
            type=str,
            default="nicos_scichat",
            settable=False,
            preinit=True,
            mandatory=False,
            userparam=False,
        ),
    }

    _producer = None

    def doInit(self, mode):
        if mode == SIMULATION:
            return
        self._producer = KafkaProducer.create(self.brokers)

    @usermethod
    def send(self, message):
        """Send the message to SciChat"""
        if not self._producer:
            return
        self._producer.produce(self.scichat_topic, self._create_message(message))

    def _create_message(self, message):
        msg = {
            "proposal": session.experiment.proposal,
            "instrument": session.instrument.name,
            "source": "NICOS",
            "message": message,
        }
        return json.dumps(msg).encode()
