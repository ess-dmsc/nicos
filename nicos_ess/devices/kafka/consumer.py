import time
import uuid

from confluent_kafka import OFFSET_END, Consumer, KafkaException, TopicPartition

from nicos.core.errors import ConfigurationError
from nicos.utils import createThread


class KafkaConsumer:
    """Class for wrapping the Confluent Kafka consumer."""

    @staticmethod
    def create(brokers, starting_offset="latest", **options):
        """Factory method for creating a consumer.

        Will automatically apply SSL settings if they are defined in the
        nicos.conf file.

        :param brokers: The broker addresses to connect to.
        :param starting_offset: Either 'latest' (default) or 'earliest'.
        :param options: Extra configuration options. See the Confluent Kafka
            documents for the full list of options.
        """
        # options = {**options, **create_sasl_config()}
        return KafkaConsumer(brokers, starting_offset, **options)

    def __init__(self, brokers, starting_offset="latest", **options):
        """
        :param brokers: The broker addresses to connect to.
        :param starting_offset: Either 'latest' (default) or 'earliest'.
        :param options: Extra configuration options. See the Confluent Kafka
            documents for the full list of options.
        """
        config = {
            "bootstrap.servers": ",".join(brokers),
            "group.id": uuid.uuid4(),
            "auto.offset.reset": starting_offset,
        }
        self._consumer = Consumer({**config, **options})

    def subscribe(self, topics):
        """Subscribe to topics.

        Note: will unsubscribe any previous subscriptions.

        :param topics: The topics to subscribe to.
        """
        topic_partitions = []
        for topic_name in topics:
            try:
                metadata = self._consumer.list_topics(topic_name, timeout=5)
            except KafkaException as exc:
                raise ConfigurationError(
                    "could not obtain metadata for topic " f"{topic_name}"
                ) from exc

            if topic_name not in metadata.topics:
                raise ConfigurationError(
                    f"provided topic {topic_name} does " "not exist"
                )

            topic_partitions.extend(
                [
                    TopicPartition(topic_name, p)
                    for p in metadata.topics[topic_name].partitions
                ]
            )

        self._consumer.assign(topic_partitions)

    def unsubscribe(self):
        """Remove any existing subscriptions."""
        self._consumer.unsubscribe()

    def poll(self, timeout_ms=5):
        """Poll for messages.

        Note: returns at most one message.

        :param timeout_ms: The poll timeout
        :return: A message or None if no message received within the
            timeout.
        """
        return self._consumer.poll(timeout_ms // 1000)

    def close(self):
        """Close the consumer."""
        self._consumer.close()

    def topics(self, timeout_s=5):
        """Get a list of topics names.

        :param timeout_s: The timeout in seconds.
        :return: A list of topic names.
        """
        return list(self._consumer.list_topics(timeout=timeout_s).topics)

    def seek(self, topic_name, partition, offset, timeout_s=5):
        """Seek to a particular offset on a partition.

        :param topic_name: The topic name.
        :param partition: The partition to seek on.
        :param offset: The required offset.
        :param timeout_s: The timeout in seconds.
        """
        topic_partition = TopicPartition(topic_name, partition)
        topic_partition.offset = offset
        self._seek([topic_partition], timeout_s)

    def _seek(self, partitions, timeout_s):
        # Seek will fail if called too soon after assign.
        # Therefore, try a few times.
        start = time.monotonic()
        while time.monotonic() < start + timeout_s:
            for part in partitions:
                try:
                    self._consumer.seek(part)
                except KafkaException:
                    time.sleep(0.1)
            return
        raise RuntimeError("failed to seek offset")

    def assignment(self):
        """
        :return: A list of assigned topic partitions.
        """
        return self._consumer.assignment()

    def seek_to_end(self, timeout_s=5):
        """Move the consumer to the end of the partition(s).

        :param timeout_s: The timeout in seconds.
        """
        partitions = self._consumer.assignment()
        for tp in partitions:
            tp.offset = OFFSET_END
        self._seek(partitions, timeout_s)


class KafkaSubscriber:
    """Continuously listens for messages on the specified topics"""

    def __init__(self, brokers):
        self._consumer = KafkaConsumer.create(brokers)
        self._polling_thread = None
        self._stop_requested = False
        self._messages_callback = None
        self._no_messages_callback = None

    def subscribe(self, topics, messages_callback, no_messages_callback=None):
        self.stop_consuming(True)

        self._consumer.unsubscribe()
        self._consumer.subscribe(topics)

        self._messages_callback = messages_callback
        self._no_messages_callback = no_messages_callback
        self._stop_requested = False
        self._polling_thread = createThread(
            f"polling_thread_{int(time.monotonic())}", self._monitor_topics
        )

    def stop_consuming(self, wait_for_join=False):
        self._stop_requested = True
        if wait_for_join and self._polling_thread:
            self._polling_thread.join()

    def close(self):
        self.stop_consuming(True)
        self._consumer.close()

    @property
    def consumer(self):
        return self._consumer

    def _monitor_topics(self):
        while not self._stop_requested:
            data = self._consumer.poll(timeout_ms=5)
            messages = []
            if data:
                messages.append((data.timestamp(), data.value()))

            if messages and self._messages_callback:
                self._messages_callback(messages)
            elif self._no_messages_callback:
                self._no_messages_callback()
            time.sleep(0.01)
