import json
import time
import uuid

from confluent_kafka import (
    OFFSET_END,
    Consumer,
    KafkaError,
    KafkaException,
    TopicPartition,
)

from nicos.core.errors import ConfigurationError
from nicos.utils import createThread
from nicos_ess.devices.kafka.utils import create_sasl_config

NO_STATS_REBOOT_SECS = 10  # if stats callback stalls
ALL_DOWN_REBOOT_SECS = 10  # if all brokers down this long
REBOOT_COOLDOWN_SECS = 15
WAIT_AFTER_ASSIGN_SECS = 12  # grace after successful (re)assign


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
        self._brokers = list(brokers)
        self._starting_offset = starting_offset
        self._user_options = dict(options)  # already merged by .create()

        group_id = options.get("group_id", f"nicos-consumer-{uuid.uuid4()}")
        options.pop("group_id", None)
        config = {
            "bootstrap.servers": ",".join(brokers),
            "group.id": group_id,
            "auto.offset.reset": starting_offset,
            "error_cb": self._on_error,
            "stats_cb": self._on_stats,
            "statistics.interval.ms": 1000,  # 1s heartbeat of stats
            # helpful defaults that don’t change semantics
            "socket.keepalive.enable": True,
            "reconnect.backoff.ms": 100,
            "reconnect.backoff.max.ms": 10_000,
        }

        self._conf_effective = {**config, **options}
        self._consumer = Consumer(self._conf_effective)

        self._last_stats_mono = time.monotonic()
        self._broker_states = {}  # name -> "UP" / "TRY_CONNECT" / ...
        self._all_down_since = None  # monotonic timestamp or None
        self._topics = []  # last subscribed topics (strings)
        self._last_assignment = []  # last assigned TopicPartition list
        self._pending_reassign = False
        self._last_rebootstrap_mono = 0.0  # debounce repeated reboots
        self._last_assign_mono = 0.0

    def brokers_up(self):
        return sum(1 for s in self._broker_states.values() if s == "UP")

    def all_brokers_down_for(self):
        if self._all_down_since is None:
            return 0.0
        return max(0.0, time.monotonic() - self._all_down_since)

    def last_stats_age(self):
        return max(0.0, time.monotonic() - self._last_stats_mono)

    def _can_fetch_metadata(
        self, topic: str | None = None, timeout_s: float = 1.0
    ) -> bool:
        """Return True if we can fetch cluster/topic metadata (broker responsive)."""
        try:
            _ = self._consumer.list_topics(topic, timeout=timeout_s)
            return True
        except KafkaException:
            return False

    def try_reassign(self) -> bool:
        """
        Attempt to (re)assign the last topics. Returns True on success, False if we
        should try later (e.g., brokers still TRY_CONNECT).
        """
        if not self._topics:
            self._pending_reassign = False
            return True

        # Require at least one broker UP or metadata reachable
        if self.brokers_up() == 0 and not self._can_fetch_metadata(None, timeout_s=0.5):
            return False

        # Re-run your discover-and-assign logic, but swallow transient errors
        topic_partitions = []
        try:
            for topic_name in self._topics:
                md = self._consumer.list_topics(topic_name, timeout=2.0)
                if topic_name not in md.topics:
                    # Topic not visible yet; try again later
                    return False
                topic_partitions.extend(
                    [
                        TopicPartition(topic_name, p)
                        for p in md.topics[topic_name].partitions
                    ]
                )
            self._consumer.assign(topic_partitions)
            self._last_assignment = list(topic_partitions)
            self._pending_reassign = False
            self._last_assign_mono = time.monotonic()
            print(
                f"[kafka-reassign] assigned to {[(tp.topic, tp.partition) for tp in topic_partitions]}"
            )
            return True
        except KafkaException as exc:
            # Metadata still not ready; try again later
            print(f"[kafka-reassign] metadata not ready yet: {exc}")
            return False

    def _on_error(self, err):
        # keep your existing prints; add quick classification
        print(
            f"[kafka-error] code={err.code()} name={err.name()} fatal={err.fatal()} "
            f"retriable={err.retriable()} msg={err.str()}"
        )

    def _on_stats(self, stats_json):
        # Parse and track broker and coordinator states; this runs ~every 1s
        print("Getting on_stats")
        self._last_stats_mono = time.monotonic()
        try:
            data = json.loads(stats_json)
        except Exception:
            print("[kafka-stats] (invalid json)")
            return

        brokers = data.get("brokers", {})
        states = {}
        for name, b in brokers.items():
            s = b.get("state")
            if s:
                states[name] = s
        # GroupCoordinator has a 'state' too; track it (helps during flaps)
        gc = data.get("brokers", {}).get("GroupCoordinator") or data.get(
            "GroupCoordinator"
        )
        if isinstance(gc, dict) and "state" in gc:
            states["GroupCoordinator"] = gc["state"]

        if states:
            self._broker_states = states
            print(states)
            up = self.brokers_up()
            if up == 0:
                if self._all_down_since is None:
                    self._all_down_since = self._last_stats_mono
            else:
                self._all_down_since = None

        # Optional: very compact broker summary log (comment out if noisy)
        # print(f"[kafka-stats] brokers_up={self.brokers_up()} "
        #       f"all_down_for={self.all_brokers_down_for():.1f}s")

    def subscribe(self, topics):
        """Manual partition assignment for the given topics (unchanged behavior)."""
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

        self._topics = list(topics)
        self._last_assignment = list(topic_partitions)
        self._pending_reassign = False
        self._last_assign_mono = time.monotonic()

    def rebootstrap(self, reason=""):
        """Close and recreate the underlying Consumer, then re-assign the last known partitions."""
        print(f"[kafka-rebootstrap] reason={reason}")
        try:
            self._consumer.close()
        except Exception as e:
            print(f"[kafka-rebootstrap] close() error (ignored): {e!r}")

        # recreate with identical config & callbacks
        self._consumer = Consumer(self._conf_effective)
        # Re-assign: re-discover partitions to cope with topology changes.
        if self._topics:
            try:
                self.subscribe(self._topics)
                print(f"[kafka-rebootstrap] re-assigned to topics={self._topics}")
            except Exception as e:
                print(f"[kafka-rebootstrap] re-assign failed: {e!r}")

        self._broker_states = {}
        self._all_down_since = None
        self._last_stats_mono = time.monotonic()
        self._pending_reassign = True
        self._last_rebootstrap_mono = time.monotonic()

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
        last_event_mono = time.monotonic()

        while not self._stop_requested:
            try:
                msg = self._consumer.poll(timeout_ms=5)

                now = time.monotonic()

                # --- NEW: attempt deferred reassign first, if any
                if self._consumer._pending_reassign:
                    # Only try when we have signs of life (brokers UP or metadata reachable)
                    assigned = self._consumer.try_reassign()
                    if not assigned:
                        # No harm in waiting a bit; stats/poll will keep the client alive
                        time.sleep(0.05)

                # --- watchdogs based on health from stats_cb, with cooldown
                since_reboot = now - self._consumer._last_rebootstrap_mono
                since_assign = now - self._consumer._last_assign_mono

                if (
                    self._consumer.all_brokers_down_for() > ALL_DOWN_REBOOT_SECS
                    and since_reboot > REBOOT_COOLDOWN_SECS
                    and since_assign > WAIT_AFTER_ASSIGN_SECS
                    and not self._consumer._pending_reassign
                ):  # don't reboot while we're waiting to reassign
                    self._consumer.rebootstrap("all_brokers_down")
                    last_event_mono = now
                    time.sleep(0.25)
                    continue

                if (
                    self._consumer.last_stats_age() > NO_STATS_REBOOT_SECS
                    and since_reboot > REBOOT_COOLDOWN_SECS
                    and since_assign > WAIT_AFTER_ASSIGN_SECS
                    and not self._consumer._pending_reassign
                ):
                    self._consumer.rebootstrap("no_stats_heartbeat")
                    last_event_mono = now
                    time.sleep(0.25)
                    continue

                # --- normal handling
                if msg is None:
                    if self._no_messages_callback:
                        self._no_messages_callback()
                    time.sleep(0.01)
                    continue

                last_event_mono = now

                if msg.error():
                    err = msg.error()
                    if err.code() == KafkaError._PARTITION_EOF:
                        pass
                    elif err.code() == KafkaError._ALL_BROKERS_DOWN:
                        print("[kafka-event] all brokers down (event)")
                    else:
                        print(
                            f"[kafka-msg-error] code={err.code()} name={err.name()} "
                            f"retriable={err.retriable()} fatal={err.fatal()} msg={err.str()}"
                        )
                    continue

                if self._messages_callback:
                    self._messages_callback([(msg.timestamp(), msg.value())])
                else:
                    time.sleep(0.01)

            except Exception as e:
                print(f"Exception in KafkaSubscriber: {e!r}")
                time.sleep(0.5)


if __name__ == "__main__":
    # Simple test / demo
    def print_messages(msgs):
        for ts, val in msgs:
            ttype, tval = ts
            print(f"msg ts={ttype}:{tval} len={len(val)}")

    def print_no_messages():
        pass
        # print("no messages")

    def create_sasl_config():
        # Dummy for testing without nicos.conf
        return {}

    brokers = ["localhost:9092"]
    topics = ["data_topic"]

    sub = KafkaSubscriber(brokers)
    sub.subscribe(topics, print_messages, print_no_messages)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    sub.close()
