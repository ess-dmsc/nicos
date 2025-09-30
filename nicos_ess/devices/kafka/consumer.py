from __future__ import annotations

import json
import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from confluent_kafka import (
    OFFSET_END,
    Consumer,
    KafkaError,
    KafkaException,
    TopicPartition,
)

from nicos import session
from nicos.core.errors import ConfigurationError
from nicos.utils import createThread
from nicos_ess.devices.kafka.utils import create_sasl_config

NO_STATS_REBOOT_SECS = 10  # stats callback stalled this long -> reboot
ALL_DOWN_REBOOT_SECS = 10  # all brokers down this long -> reboot
REBOOT_COOLDOWN_SECS = 15  # minimum time between reboots
REBOOT_JITTER_SECS = 3  # random jitter to avoid thundering herds
WAIT_AFTER_ASSIGN_SECS = 12  # grace period after (re)assign before we consider reboot
MAX_BATCH_SIZE = 100  # max messages per consume() burst in subscriber


def _now_mono() -> float:
    return time.monotonic()


def _cooldown_ok(last_ts: float, min_secs: float) -> bool:
    return (_now_mono() - last_ts) >= min_secs


@dataclass
class _Health:
    last_stats_mono: float = _now_mono()
    all_down_since: Optional[float] = None
    brokers_state: dict = None  # name -> state string (UP, DOWN, TRY_CONNECT, ...)

    def __post_init__(self):
        if self.brokers_state is None:
            self.brokers_state = {}

    def brokers_up(self) -> int:
        return sum(1 for s in self.brokers_state.values() if s == "UP")

    def last_stats_age(self) -> float:
        return max(0.0, _now_mono() - self.last_stats_mono)

    def all_down_for(self) -> float:
        if self.all_down_since is None:
            return 0.0
        return max(0.0, _now_mono() - self.all_down_since)


class KafkaConsumer:
    """Wrapper around Confluent Kafka Consumer with robust watchdogs."""

    @staticmethod
    def create(
        brokers: Sequence[str], starting_offset: str = "latest", **options
    ) -> "KafkaConsumer":
        options = {**options, **create_sasl_config()}
        return KafkaConsumer(brokers, starting_offset, **options)

    def __init__(
        self, brokers: Sequence[str], starting_offset: str = "latest", **options
    ):
        self._brokers = list(brokers)
        self._starting_offset = starting_offset
        self._user_options = dict(options)

        group_id = options.get("group_id", f"nicos-consumer-{uuid.uuid4()}")
        options.pop("group_id", None)

        base_conf = {
            "bootstrap.servers": ",".join(brokers),
            "group.id": group_id,
            "auto.offset.reset": starting_offset,
            "error_cb": self._on_error,
            "stats_cb": self._on_stats,
            "statistics.interval.ms": 1000,  # 1s stats heartbeat (served from poll/consume)
            "socket.keepalive.enable": True,
            "reconnect.backoff.ms": 100,
            "reconnect.backoff.max.ms": 10_000,
            "allow.auto.create.topics": False,
            "api.version.request": True,
            "enable.auto.commit": False,
            "enable.partition.eof": True,
            "client.id": f"nicos-consumer-{uuid.uuid4()}",
        }

        self._conf_effective = {**base_conf, **options}
        self._consumer = Consumer(self._conf_effective)

        self._health = _Health()
        self._topics: List[str] = []
        self._last_assignment: List[TopicPartition] = []
        self._pending_reassign: bool = False
        self._last_rebootstrap_mono: float = 0.0
        self._last_assign_mono: float = 0.0

        # Thread-safety: librdkafka handles its own threads, but the Python Consumer
        # object itself is not thread-safe. Guard all calls with this lock.
        self._lock = threading.RLock()

    def brokers_up(self) -> int:
        return self._health.brokers_up()

    def all_brokers_down_for(self) -> float:
        return self._health.all_down_for()

    def last_stats_age(self) -> float:
        return self._health.last_stats_age()

    def _can_fetch_metadata(
        self, topic: Optional[str] = None, timeout_s: float = 1.0
    ) -> bool:
        """Return True if broker responds to metadata.
        Uses list_topics(None) by default to avoid accidental topic creation.
        """
        try:
            with self._lock:
                _ = self._consumer.list_topics(
                    None if topic is None else topic, timeout=timeout_s
                )
            return True
        except KafkaException:
            return False

    def try_reassign(self) -> bool:
        """Attempt to (re)assign the last topics. Return True on success.
        Will refuse if there’s no sign of broker responsiveness yet.
        """
        if not self._topics:
            self._pending_reassign = False
            return True

        if self.brokers_up() == 0 and not self._can_fetch_metadata(None, timeout_s=0.5):
            return False

        try:
            with self._lock:
                # Fetch all topics’ metadata in one call to avoid per-topic creation side-effects
                md = self._consumer.list_topics(None, timeout=2.0)
                topic_partitions: List[TopicPartition] = []
                for topic_name in self._topics:
                    tmeta = md.topics.get(topic_name)
                    if tmeta is None or tmeta.error is not None:
                        # Not visible yet; try later
                        return False
                    topic_partitions.extend(
                        TopicPartition(topic_name, p) for p in tmeta.partitions
                    )
                self._consumer.assign(topic_partitions)

            self._last_assignment = list(topic_partitions)
            self._pending_reassign = False
            self._last_assign_mono = _now_mono()
            session.log.info(
                "[kafka] (re)assigned partitions: %s",
                [(tp.topic, tp.partition) for tp in topic_partitions],
            )
            return True
        except KafkaException as exc:
            session.log.debug("[kafka] metadata not ready yet during reassign: %r", exc)
            return False

    def _on_error(self, err: KafkaError):
        # Informational errors are frequent; escalate only when fatal.
        session.log.warning(
            "[kafka-error] code=%s name=%s fatal=%s retriable=%s msg=%s",
            err.code(),
            err.name(),
            err.fatal(),
            err.retriable(),
            err.str(),
        )
        if err.fatal():
            # Don’t spin — respect cooldown + jitter
            if _cooldown_ok(self._last_rebootstrap_mono, REBOOT_COOLDOWN_SECS):
                self.rebootstrap("fatal_error:%s" % err.name())

    def _on_stats(self, stats_json: str):
        # Called ~every statistics.interval.ms, but only when poll/consume are called.
        self._health.last_stats_mono = _now_mono()
        try:
            data = json.loads(stats_json)
        except Exception:
            session.log.debug("[kafka-stats] invalid json")
            return

        # Track broker states
        brokers = data.get("brokers", {}) or {}
        states = {}
        for name, b in brokers.items():
            st = b.get("state")
            if st:
                states[name] = st

        # Consumer-group / coordinator state (stats JSON typically exposes under 'cgrp')
        cgrp = data.get("cgrp") or {}
        if isinstance(cgrp, dict):
            cg_state = cgrp.get("state")
            if cg_state:
                states["GroupCoordinator"] = str(cg_state).upper()

        if states:
            self._health.brokers_state = states
            up = self.brokers_up()
            if up == 0:
                if self._health.all_down_since is None:
                    self._health.all_down_since = self._health.last_stats_mono
            else:
                self._health.all_down_since = None

    def subscribe(self, topics: Sequence[str]):
        """Manual partition assignment for the given topics (unchanged behavior)."""
        # Validate topics using a *cluster-wide* metadata request to avoid accidental creation.
        with self._lock:
            try:
                md = self._consumer.list_topics(None, timeout=5)
            except KafkaException as exc:
                raise ConfigurationError("could not obtain cluster metadata") from exc

        topic_partitions: List[TopicPartition] = []
        for topic_name in topics:
            tmeta = md.topics.get(topic_name)
            if tmeta is None:
                raise ConfigurationError(f"provided topic {topic_name} does not exist")
            if getattr(tmeta, "error", None) is not None:
                raise ConfigurationError(
                    f"metadata for topic {topic_name} returned error: {tmeta.error}"
                )
            topic_partitions.extend(
                TopicPartition(topic_name, p) for p in tmeta.partitions
            )

        with self._lock:
            self._consumer.assign(topic_partitions)

        self._topics = list(topics)
        self._last_assignment = list(topic_partitions)
        self._pending_reassign = False
        self._last_assign_mono = _now_mono()
        session.log.info(
            "[kafka] assigned partitions: %s",
            [(tp.topic, tp.partition) for tp in topic_partitions],
        )

    def rebootstrap(self, reason: str = ""):
        """Close and recreate the underlying Consumer, then re-assign last partitions."""
        jitter = random.uniform(0, REBOOT_JITTER_SECS)
        session.log.warning(
            "[kafka-rebootstrap] reason=%s (jitter=%.2fs)", reason, jitter
        )
        time.sleep(jitter)

        try:
            with self._lock:
                self._consumer.close()
        except Exception as e:
            session.log.debug("[kafka-rebootstrap] close() error ignored: %r", e)

        with self._lock:
            self._consumer = Consumer(self._conf_effective)

        reassigned_ok = False
        if self._topics:
            try:
                self.subscribe(self._topics)
                reassigned_ok = True
                session.log.info(
                    "[kafka-rebootstrap] re-assigned to topics=%s", self._topics
                )
            except Exception as e:
                session.log.warning("[kafka-rebootstrap] re-assign failed: %r", e)

        # Reset health & flags
        self._health = _Health()
        self._pending_reassign = not reassigned_ok and bool(self._topics)
        self._last_rebootstrap_mono = _now_mono()

    def unsubscribe(self):
        with self._lock:
            self._consumer.unsubscribe()

    def poll(self, timeout_ms: int = 5):
        with self._lock:
            return self._consumer.poll(timeout_ms / 1000.0)

    def consume_batch(self, max_messages: int = MAX_BATCH_SIZE, timeout_s: float = 0.2):
        if max_messages <= 0:
            return []
        with self._lock:
            try:
                return self._consumer.consume(
                    num_messages=max_messages, timeout=timeout_s
                )
            except KafkaException as exc:
                # Bubble up as empty; loop will handle errors via .error() per-message or session.log.
                session.log.debug("[kafka] consume() raised: %r", exc)
                return []

    def close(self):
        with self._lock:
            self._consumer.close()

    def topics(self, timeout_s: float = 5) -> List[str]:
        with self._lock:
            return list(self._consumer.list_topics(timeout=timeout_s).topics)

    def seek(self, topic_name: str, partition: int, offset: int, timeout_s: float = 5):
        tp = TopicPartition(topic_name, partition, offset)
        self._seek([tp], timeout_s)

    def _seek(self, partitions: Sequence[TopicPartition], timeout_s: float):
        deadline = _now_mono() + max(0.0, timeout_s)
        remaining = set((tp.topic, tp.partition, tp.offset) for tp in partitions)
        last_err: Optional[Exception] = None
        while remaining and _now_mono() < deadline:
            done_now = []
            for topic, part, off in list(remaining):
                tp = TopicPartition(topic, part, off)
                try:
                    with self._lock:
                        self._consumer.seek(tp)
                    done_now.append((topic, part, off))
                except KafkaException as e:
                    last_err = e
                    time.sleep(0.1)
            for item in done_now:
                remaining.discard(item)
        if remaining:
            raise RuntimeError(
                f"failed to seek offsets for: {sorted(remaining)}; last_err={last_err!r}"
            )

    def assignment(self) -> List[TopicPartition]:
        with self._lock:
            return self._consumer.assignment()

    def seek_to_end(self, timeout_s: float = 5):
        with self._lock:
            partitions = self._consumer.assignment()
        for tp in partitions:
            tp.offset = OFFSET_END
        self._seek(partitions, timeout_s)


class KafkaSubscriber:
    """Continuously listens for messages on the specified topics."""

    def __init__(self, brokers: Sequence[str]):
        self._consumer = KafkaConsumer.create(brokers)
        self._polling_thread = None
        self._stop_event = threading.Event()
        self._messages_callback = None
        self._no_messages_callback = None

    def subscribe(
        self, topics: Sequence[str], messages_callback, no_messages_callback=None
    ):
        self.stop_consuming(True)

        self._consumer.unsubscribe()
        self._consumer.subscribe(topics)

        self._messages_callback = messages_callback
        self._no_messages_callback = no_messages_callback
        self._stop_event.clear()
        self._polling_thread = createThread(
            f"polling_thread_{int(_now_mono())}", self._monitor_topics
        )

    def stop_consuming(self, wait_for_join: bool = False):
        self._stop_event.set()
        if wait_for_join and self._polling_thread:
            self._polling_thread.join()

    def close(self):
        self.stop_consuming(True)
        self._consumer.close()

    @property
    def consumer(self) -> KafkaConsumer:
        return self._consumer

    def _monitor_topics(self):
        last_event_mono = _now_mono()
        last_no_msg_cb = 0.0
        idle_backoff = 0.01  # seconds; grows to 0.2s when idle

        while not self._stop_event.is_set():
            try:
                now = _now_mono()

                # Attempt deferred reassign early, if any
                if self._consumer._pending_reassign:
                    assigned = self._consumer.try_reassign()
                    if not assigned:
                        time.sleep(0.05)

                # Watchdogs (reboot only after grace window & cooldown)
                since_reboot = now - self._consumer._last_rebootstrap_mono
                since_assign = now - self._consumer._last_assign_mono

                if (
                    self._consumer.all_brokers_down_for() > ALL_DOWN_REBOOT_SECS
                    and _cooldown_ok(
                        self._consumer._last_rebootstrap_mono, REBOOT_COOLDOWN_SECS
                    )
                    and since_assign > WAIT_AFTER_ASSIGN_SECS
                    and not self._consumer._pending_reassign
                ):
                    self._consumer.rebootstrap("all_brokers_down")
                    last_event_mono = now
                    time.sleep(0.25)
                    continue

                if (
                    self._consumer.last_stats_age() > NO_STATS_REBOOT_SECS
                    and _cooldown_ok(
                        self._consumer._last_rebootstrap_mono, REBOOT_COOLDOWN_SECS
                    )
                    and since_assign > WAIT_AFTER_ASSIGN_SECS
                    and not self._consumer._pending_reassign
                ):
                    self._consumer.rebootstrap("no_stats_heartbeat")
                    last_event_mono = now
                    time.sleep(0.25)
                    continue

                # Consume messages, let's try if that works instead of poll()
                msgs = self._consumer.consume_batch(MAX_BATCH_SIZE, timeout_s=0.05)
                deliver: List[Tuple[Tuple[int, int], bytes]] = []
                had_error = False
                for m in msgs:
                    if m is None:
                        continue
                    if m.error():
                        err = m.error()
                        had_error = True
                        if err.code() == KafkaError._PARTITION_EOF:
                            # benign: end-of-partition marker
                            pass
                        elif err.code() == KafkaError._ALL_BROKERS_DOWN:
                            session.log.warning(
                                "[kafka-event] all brokers down (event)"
                            )
                        else:
                            session.log.warning(
                                "[kafka-msg-error] code=%s name=%s retriable=%s fatal=%s msg=%s",
                                err.code(),
                                err.name(),
                                err.retriable(),
                                err.fatal(),
                                err.str(),
                            )
                        continue
                    deliver.append((m.timestamp(), m.value()))

                if deliver:
                    last_event_mono = now
                    idle_backoff = 0.01
                    if self._messages_callback:
                        try:
                            self._messages_callback(deliver)
                        except Exception:
                            session.log.error("[kafka] messages_callback raised")
                else:
                    # Rate-limit no_messages_callback to ~10/s max
                    if self._no_messages_callback and (now - last_no_msg_cb) > 0.1:
                        try:
                            self._no_messages_callback()
                        except Exception:
                            session.log.error("[kafka] no_messages_callback raised")
                        last_no_msg_cb = now

                    idle_backoff = min(
                        0.2, idle_backoff * (1.5 if not had_error else 1.0)
                    )
                    time.sleep(idle_backoff)

            except Exception as e:
                session.log.error("Exception in KafkaSubscriber loop: %r", e)
                time.sleep(0.5)


if __name__ == "__main__":
    # Simple test / demo
    # make sure you have a local Kafka broker running with topic "data_topic"
    def print_messages(msgs):
        for ts, val in msgs:
            ttype, tval = ts
            print(f"msg ts={ttype}:{tval} len={len(val) if val is not None else 0}")

    def print_no_messages():
        pass

    def create_sasl_config():
        return {}

    # override logging for local testing
    class session:
        log = logging.getLogger("kafka_consumer_demo")
        log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        log.addHandler(ch)

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
