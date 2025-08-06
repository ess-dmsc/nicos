import time
import uuid

from confluent_kafka import OFFSET_END, Consumer, KafkaException, TopicPartition

from nicos import session
from nicos.core.errors import ConfigurationError
from nicos.utils import createThread
from nicos_ess.devices.kafka.utils import create_sasl_config


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
        options = {**options, **create_sasl_config()}
        return KafkaConsumer(brokers, starting_offset, **options)

    def __init__(self, brokers, starting_offset="latest", **options):
        """
        :param brokers: The broker addresses to connect to.
        :param starting_offset: Either 'latest' (default) or 'earliest'.
        :param options: Extra configuration options. See the Confluent Kafka
            documents for the full list of options.
        """
        # check if group.id is provided in options
        group_id = options.get("group_id", f"nicos-consumer-{uuid.uuid4()}")
        options.pop("group_id", None)
        config = {
            "bootstrap.servers": ",".join(brokers),
            "group.id": group_id,
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
                    f"could not obtain metadata for topic {topic_name}"
                ) from exc

            if topic_name not in metadata.topics:
                raise ConfigurationError(f"provided topic {topic_name} does not exist")

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
        return self._consumer.poll(timeout_ms / 1000)

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

    def offsets_for_times(self, topic_partitions, timeout_s=5):
        """
        Return TopicPartition entries with offsets at/after the given timestamps.

        :param topic_partitions: list[TopicPartition] with .offset set to a timestamp (ms since epoch)
        :param timeout_s: timeout for the underlying call
        :return: list[TopicPartition] with .offset set to the corresponding offsets
        """
        return self._consumer.offsets_for_times(topic_partitions, timeout=timeout_s)

    def get_high_watermark_offsets(self, timeout_s=5):
        """
        Get the current high watermark offsets for all assigned partitions.

        :param timeout_s: timeout for metadata operations
        :return: dict[TopicPartition, high_offset]
        """
        assigned = self._consumer.assignment()
        if not assigned:
            return []

        return {
            (tp.topic, tp.partition): self._consumer.get_watermark_offsets(
                tp, timeout=timeout_s
            )[1]
            for tp in assigned
        }

    def seek_all_assigned_to_timestamp(self, timestamp_ms, timeout_s=5):
        """
        Seek all currently assigned partitions to the first offset at/after timestamp_ms.

        :param timestamp_ms: milliseconds since Unix epoch
        :param timeout_s: timeout for metadata/seek operations
        """
        assigned = self._consumer.assignment()
        if not assigned:
            return

        req = []
        for tp in assigned:
            req.append(TopicPartition(tp.topic, tp.partition, timestamp_ms))

        resolved = self._consumer.offsets_for_times(req, timeout=timeout_s)

        to_seek = []
        for tp in resolved:
            if tp.offset is not None and tp.offset >= 0:
                to_seek.append(TopicPartition(tp.topic, tp.partition, tp.offset))
        if to_seek:
            self._seek(to_seek, timeout_s)


class KafkaSubscriber:
    """Continuously listens for messages on the specified topics"""

    def __init__(self, brokers):
        self._consumer = KafkaConsumer.create(brokers)
        self._polling_thread = None
        self._stop_requested = False
        self._messages_callback = None
        self._no_messages_callback = None
        self._last_msg_ts_monotonic = time.monotonic()
        self._topics = []
        self._brokers = brokers
        self._resub_attempts = 0
        self._cooldown_until = 0.0
        self._resubscribe_after_s = 30
        self._resubscribe_active = False

    def subscribe(self, topics, messages_callback, no_messages_callback=None):
        self.stop_consuming(True)

        self._consumer.unsubscribe()
        self._consumer.subscribe(topics)
        self._topics = topics

        self._messages_callback = messages_callback
        self._no_messages_callback = no_messages_callback
        self._stop_requested = False
        self._polling_thread = createThread(
            f"polling_thread_{int(time.monotonic())}", self._monitor_topics
        )

    def set_resubscribe(self, resubscribe_after_s=30, active=True):
        """Set the resubscribe parameters.
        :param resubscribe_after_s: Time in seconds after which to resubscribe if no messages are received.
        :param active: Whether to enable resubscription.
        """
        self._resubscribe_after_s = resubscribe_after_s
        self._resubscribe_active = active
        self._last_msg_ts_monotonic = time.monotonic()

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
            try:
                data = self._consumer.poll(timeout_ms=5)
            except Exception as e:
                session.log.error(f"Error polling Kafka consumer: {e}")
                time.sleep(0.1)
                continue
            messages = []
            if data:
                messages.append((data.timestamp(), data.value()))
                self._last_msg_ts_monotonic = time.monotonic()

            if messages and self._messages_callback:
                self._messages_callback(messages)
            elif self._no_messages_callback:
                self._no_messages_callback()
                time.sleep(0.01)
            else:
                time.sleep(0.01)

            now = time.monotonic()
            if (
                self._resubscribe_active
                and now - self._last_msg_ts_monotonic > self._resubscribe_after_s
                and now >= self._cooldown_until
            ):
                try:
                    self._consumer.unsubscribe()
                    self._consumer.subscribe(self._topics)
                except Exception:
                    pass
                finally:
                    self._last_msg_ts_monotonic = time.monotonic()
                    self._resub_attempts += 1
                    backoff = min(
                        30.0, 2.0 ** min(5, self._resub_attempts)
                    )  # cap at 32s
                    self._cooldown_until = now + backoff
                    if self._resub_attempts >= 3:
                        # full recreate after a few silent resubs
                        try:
                            self._consumer.close()
                        except Exception:
                            pass
                        self._consumer = KafkaConsumer.create(self._brokers)
                        try:
                            self._consumer.subscribe(self._topics)
                        except Exception:
                            pass
                        self._resub_attempts = 0
