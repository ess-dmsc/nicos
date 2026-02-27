from typing import Optional

from confluent_kafka import Producer

from nicos.core import DeviceMixinBase, Param, host, listof
from nicos.core.constants import SIMULATION
from nicos_ess.devices.kafka.utils import create_sasl_config

MAX_MESSAGE_SIZE = 209_715_200


class KafkaProducer:
    """Class for wrapping the Confluent Kafka producer."""

    @staticmethod
    def create(brokers, **options):
        """Factory method for creating a producer.

        Will automatically apply SSL settings if they are defined in the
        nicos.conf file.

        :param brokers: The broker addresses to connect to.
        :param options: Extra configuration options. See the Confluent Kafka
            documents for the full list of options.
        """
        options = {**options, **create_sasl_config()}
        return KafkaProducer(brokers, **options)

    def __init__(self, brokers, **options):
        """
        :param brokers: The broker addresses to connect to.
        :param options: Extra configuration options. See the Confluent Kafka
            documents for the full list of options.
        """
        config = {
            "bootstrap.servers": ",".join(brokers),
            "message.max.bytes": MAX_MESSAGE_SIZE,
            "linger.ms": 20,
            "batch.num.messages": 10000,
            "message.timeout.ms": 60000,
        }
        self._producer = Producer({**config, **options})

    def produce(
        self,
        topic_name,
        message,
        partition=-1,
        key=None,
        on_delivery_callback=None,
        *,
        auto_flush: bool = True,
        flush_timeout: Optional[float] = None,  # seconds, None = block indefinitely
        poll_before_produce: bool = True,
    ):
        """Send a message to Kafka.

        :param topic_name: The topic to send to.
        :param message: The message.
        :param partition: Which partition to send to. Optional.
        :param key: The key to assign. Optional
        :param on_delivery_callback: The delivery callback. Optional.
        :param auto_flush: Whether to flush after producing. If False, the caller is responsible for calling flush() to ensure messages are sent.
        :param flush_timeout: If auto_flush is True, how long to block for the flush (in seconds). None means block indefinitely until all messages are flushed.
        :param poll_before_produce: Whether to call poll() before producing to serve delivery reports and internal events. This is important to do if auto_flush is False, otherwise delivery callbacks may not be called.

        Backwards compatible:
          - auto_flush=True -> same semantics as before (produce + flush)
          - auto_flush=False -> async enqueue only (no flush)
        """

        # Serve delivery reports / internal events (important when not flushing).
        if poll_before_produce:
            self._producer.poll(0)

        self._producer.produce(
            topic_name,
            message,
            partition=partition,
            key=key,
            on_delivery=on_delivery_callback,
        )

        if auto_flush:
            # Keep legacy behavior: block until delivered (or until timeout if provided)
            self.flush(flush_timeout)

    def flush(self, timeout: Optional[float] = None) -> int:
        """Expose flush so callers can batch + flush explicitly."""
        # apparently None is not accepted by the underlying library, so we need to handle it ourselves
        # def flush(self, timeout=None): # real signature unknown; restored from __doc__
        if timeout is None:
            return self._producer.flush()
        return self._producer.flush(timeout)

    def poll(self, timeout: float = 0.0) -> int:
        return self._producer.poll(timeout)


class ProducesKafkaMessages(DeviceMixinBase):
    """Device to produce messages to kafka. The method *send* can be used
    to produce a timestamped message onto the topic. Kafka brokers
    can be specified using the parameter *brokers*.
    """

    parameters = {
        "brokers": Param(
            "List of kafka brokers to connect to",
            type=listof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "max_request_size": Param(
            "Maximum size of kafka message",
            type=int,
            default=16000000,
            preinit=True,
            userparam=False,
        ),
    }

    def doPreinit(self, mode):
        if mode != SIMULATION:
            self._producer = self._create_producer(
                max_request_size=self.max_request_size
            )
        else:
            self._producer = None

    def _create_producer(self, **options):
        return KafkaProducer.create(self.brokers, **options)

    def _setProducerConfig(self, **configs):
        self._producer = self._create_producer(**configs)

    def send(self, topic, message):
        """
        Produces and flushes the provided message
        :param topic: Topic on which the message is to be produced
        :param message: Message
        :return:
        """
        self._producer.produce(topic, message)
        self._producer.flush()
