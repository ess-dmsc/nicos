from __future__ import annotations

import json
import random
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from confluent_kafka import (
    OFFSET_BEGINNING,
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

NO_STATS_REBOOT_SECS = 10
ALL_DOWN_REBOOT_SECS = 10
REBOOT_COOLDOWN_SECS = 15
REBOOT_JITTER_SECS = 3
WAIT_AFTER_ASSIGN_SECS = 12
MAX_BATCH_SIZE = 100
STUCK_WITH_LAG_SECS = (
    8.0  # no deliveries for this long while lag >= threshold -> reboot
)
MIN_LAG_FOR_STUCK = 1
PARTITION_PROBE_INTERVAL_SECS = 10.0  # how often to check for partition count changes


@dataclass
class _Health:
    last_stats_mono: float = time.monotonic()
    all_down_since: Optional[float] = None
    brokers_state: dict = None
    group_coordinator_state: Optional[str] = None
    # Stats-derived lag view (more resilient than watermarks when RPCs fail)
    stats_total_lag: int = 0
    stats_by_tp: Dict[tuple, dict] = (
        None  # (topic,part) -> {'lag': int, 'fetch_state': str}
    )

    def __post_init__(self):
        if self.brokers_state is None:
            self.brokers_state = {}
        if self.stats_by_tp is None:
            self.stats_by_tp = {}

    def brokers_up(self) -> int:
        return sum(1 for s in self.brokers_state.values() if s == "UP")

    def group_coordinator_up(self) -> bool:
        return self.group_coordinator_state == "UP"


class KafkaConsumer:
    """Manual-assign consumer wrapper with robust watchdogs (API compatible)."""

    @staticmethod
    def create(
        brokers: Sequence[str], starting_offset: str = "latest", **options
    ) -> "KafkaConsumer":
        options = {**options, **create_sasl_config()}
        return KafkaConsumer(brokers, starting_offset, **options)

    def __init__(
        self,
        brokers: Sequence[str],
        starting_offset: str = "latest",
        *,
        consumer_factory: Callable[[dict], object] = lambda conf: Consumer(conf),
        topic_partition_factory: Callable[..., TopicPartition] = (
            lambda t, p, o=OFFSET_END: TopicPartition(t, p, o)
        ),
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        rand_uniform: Callable[[float, float], float] = random.uniform,
        on_rebootstrap: Optional[Callable[[str], None]] = None,
        **options,
    ):
        self._brokers = list(brokers)
        self._starting_offset = starting_offset
        self._user_options = dict(options)
        self._tp_factory = topic_partition_factory
        self._now = now
        self._sleep = sleep
        self._rand_uniform = rand_uniform
        self._on_rebootstrap = on_rebootstrap

        group_id = options.get("group_id", f"nicos-consumer-{uuid.uuid4()}")
        options.pop("group_id", None)

        base_conf = {
            "bootstrap.servers": ",".join(brokers),
            "group.id": group_id,
            "auto.offset.reset": starting_offset,
            "error_cb": self._on_error,
            "stats_cb": self._on_stats,
            "statistics.interval.ms": 1000,
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
        self._consumer_factory = consumer_factory
        self._consumer = consumer_factory(self._conf_effective)

        self._health = _Health()
        self._topics: List[str] = []
        self._last_assignment: List[TopicPartition] = []
        self._pending_reassign: bool = False
        self._last_rebootstrap_mono: float = 0.0
        self._last_assign_mono: float = 0.0

        # Partition change detection
        self._last_meta_probe: float = 0.0
        self._partitions_known: Dict[str, int] = {}

        self._lock = threading.RLock()

    # --------------------------
    # Health helpers
    # --------------------------
    def brokers_up(self) -> int:
        return self._health.brokers_up()

    def all_brokers_down_for(self) -> float:
        if self._health.all_down_since is None:
            return 0.0
        return max(0.0, self._now() - self._health.all_down_since)

    def last_stats_age(self) -> float:
        return max(0.0, self._now() - self._health.last_stats_mono)

    # --------------------------
    # Metadata helpers
    # --------------------------
    def _can_fetch_metadata(
        self, topic: Optional[str] = None, timeout_s: float = 1.0
    ) -> bool:
        try:
            with self._lock:
                _ = self._consumer.list_topics(
                    None if topic is None else topic, timeout=timeout_s
                )
            return True
        except KafkaException:
            return False

    def _maybe_refresh_partitions(
        self, interval_s: float = PARTITION_PROBE_INTERVAL_SECS
    ):
        """Detect topic partition count changes and trigger reassign."""
        now = self._now()
        if now - self._last_meta_probe < interval_s or not self._topics:
            return
        self._last_meta_probe = now
        try:
            with self._lock:
                md = self._consumer.list_topics(None, timeout=2.0)
            changed = False
            for t in self._topics:
                tmeta = md.topics.get(t)
                if not tmeta or getattr(tmeta, "error", None) is not None:
                    continue
                count = len(tmeta.partitions)
                if self._partitions_known.get(t) != count:
                    self._partitions_known[t] = count
                    changed = True
            if changed:
                session.log.warning(
                    "[kafka] partition count change detected; scheduling reassign"
                )
                self._pending_reassign = True
        except Exception as e:
            session.log.debug("[kafka] metadata probe failed: %r", e)

    def try_reassign(self) -> bool:
        if not self._topics:
            self._pending_reassign = False
            return True

        if self.brokers_up() == 0 and not self._can_fetch_metadata(None, timeout_s=0.5):
            return False

        try:
            with self._lock:
                md = self._consumer.list_topics(None, timeout=2.0)
                topic_partitions: List[TopicPartition] = []
                for topic_name in self._topics:
                    tmeta = md.topics.get(topic_name)
                    if tmeta is None or tmeta.error is not None:
                        return False
                    # Build partitions (offset honoring is left to seek-on-error and explicit seeks)
                    for p in tmeta.partitions:
                        topic_partitions.append(self._tp_factory(topic_name, p))
                    # Update known counts
                    self._partitions_known[topic_name] = len(tmeta.partitions)
                self._consumer.assign(topic_partitions)

            self._last_assignment = list(topic_partitions)
            self._pending_reassign = False
            self._last_assign_mono = self._now()
            session.log.info(
                "[kafka] (re)assigned partitions: %s",
                [(tp.topic, tp.partition) for tp in topic_partitions],
            )
            return True
        except KafkaException as exc:
            session.log.debug("[kafka] metadata not ready yet during reassign: %r", exc)
            return False

    # --------------------------
    # Callbacks
    # --------------------------
    def _on_error(self, err):
        try:
            session.log.warning(
                "[kafka-error] code=%s name=%s fatal=%s retriable=%s msg=%s",
                err.code(),
                err.name(),
                err.fatal(),
                err.retriable(),
                err.str(),
            )
            if err.fatal():
                if (self._now() - self._last_rebootstrap_mono) >= REBOOT_COOLDOWN_SECS:
                    self.rebootstrap("fatal_error:%s" % err.name())
        except Exception:
            session.log.warning("[kafka-error] %r", err)

    def _on_stats(self, stats_json: str):
        self._health.last_stats_mono = self._now()
        try:
            data = json.loads(stats_json)
        except Exception:
            session.log.debug("[kafka-stats] invalid json")
            return

        brokers = data.get("brokers", {}) or {}
        states = {}
        for name, b in brokers.items():
            st = b.get("state")
            if st:
                states[name] = st

        cgrp = data.get("cgrp") or {}
        if isinstance(cgrp, dict):
            cg_state = cgrp.get("state")
            if cg_state:
                self._health.group_coordinator_state = str(cg_state).upper()

        if states:
            self._health.brokers_state = states
            up = self.brokers_up()
            if up == 0:
                if self._health.all_down_since is None:
                    self._health.all_down_since = self._health.last_stats_mono
            else:
                self._health.all_down_since = None

        # Parse per-topic/partition lag from stats to avoid silent 0s
        topics = data.get("topics") or {}
        total = 0
        by_tp: Dict[tuple, dict] = {}
        for tname, tinfo in topics.items():
            parts = (tinfo or {}).get("partitions") or {}
            for pstr, pinfo in parts.items():
                try:
                    tp = (tname, int(pstr))
                    lag = pinfo.get("consumer_lag", pinfo.get("lag", 0))
                    lag = int(lag or 0)
                    fetch_state = pinfo.get("fetch_state")
                    by_tp[tp] = {"lag": max(0, lag), "fetch_state": fetch_state}
                    total += max(0, lag)
                except Exception:
                    pass
        self._health.stats_by_tp = by_tp
        self._health.stats_total_lag = max(0, int(total))

    # --------------------------
    # Control plane
    # --------------------------
    def subscribe(self, topics: Sequence[str]):
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
            for p in tmeta.partitions:
                topic_partitions.append(self._tp_factory(topic_name, p))
            self._partitions_known[topic_name] = len(tmeta.partitions)

        with self._lock:
            self._consumer.assign(topic_partitions)

        self._topics = list(topics)
        self._last_assignment = list(topic_partitions)
        self._pending_reassign = False
        self._last_assign_mono = self._now()
        session.log.info(
            "[kafka] assigned partitions: %s",
            [(tp.topic, tp.partition) for tp in topic_partitions],
        )

    def rebootstrap(self, reason: str = ""):
        if self._on_rebootstrap:
            try:
                self._on_rebootstrap(reason)
            except Exception:
                session.log.debug("[kafka-rebootstrap] on_rebootstrap hook failed")

        jitter = float(self._rand_uniform(0, REBOOT_JITTER_SECS))
        session.log.warning(
            "[kafka-rebootstrap] reason=%s (jitter=%.2fs)", reason, jitter
        )
        self._sleep(jitter)

        try:
            with self._lock:
                self._consumer.close()
        except Exception as e:
            session.log.debug("[kafka-rebootstrap] close() error ignored: %r", e)

        with self._lock:
            self._consumer = self._consumer_factory(self._conf_effective)

        reassigned_ok = False
        if self._topics:
            try:
                self.subscribe(self._topics)
                reassigned_ok = True
                session.log.info(
                    "[kafka-rebootstrap] re-subscribed to topics=%s", self._topics
                )
            except Exception as e:
                session.log.warning("[kafka-rebootstrap] re-subscribe failed: %r", e)

        self._health = _Health()
        self._pending_reassign = not reassigned_ok and bool(self._topics)
        self._last_rebootstrap_mono = self._now()

    def unsubscribe(self):
        with self._lock:
            try:
                self._consumer.unsubscribe()
            except Exception:
                pass

    # --------------------------
    # Data plane
    # --------------------------
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
                session.log.debug("[kafka] consume() raised: %r", exc)
                return []

    def close(self):
        with self._lock:
            try:
                self._consumer.close()
            except Exception:
                pass

    def topics(self, timeout_s: float = 5) -> List[str]:
        with self._lock:
            return list(self._consumer.list_topics(timeout=timeout_s).topics)

    def seek(self, topic_name: str, partition: int, offset: int, timeout_s: float = 5):
        tp = self._tp_factory(topic_name, partition, offset)
        self._seek([tp], timeout_s)

    def _seek(self, partitions: Sequence[TopicPartition], timeout_s: float):
        deadline = self._now() + max(0.0, timeout_s)
        remaining = set((tp.topic, tp.partition, tp.offset) for tp in partitions)
        last_err: Optional[Exception] = None
        while remaining and self._now() < deadline:
            done_now = []
            for topic, part, off in list(remaining):
                tp = self._tp_factory(topic, part, off)
                try:
                    with self._lock:
                        self._consumer.seek(tp)
                    done_now.append((topic, part, off))
                except KafkaException as e:
                    last_err = e
                    self._sleep(0.1)
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

    def seek_to_beginning(self, timeout_s: float = 5):
        with self._lock:
            partitions = self._consumer.assignment()
        for tp in partitions:
            tp.offset = OFFSET_BEGINNING
        self._seek(partitions, timeout_s)


class KafkaSubscriber:
    """
    Threaded message pump with watchdogs and DI-friendly single-iteration `tick()`.

    Watchdogs:
      1) all_brokers_down_for() > ALL_DOWN_REBOOT_SECS -> rebootstrap
      2) last_stats_age() > NO_STATS_REBOOT_SECS -> rebootstrap
      3) stuck-with-lag -> rebootstrap if (lag >= min_lag) and no deliveries for N seconds
      4) empty reads while stats lag > 0 -> rebootstrap
      5) lost assignment after grace -> reassign
    """

    def __init__(
        self,
        brokers: Sequence[str] | None = None,
        *,
        consumer: Optional[KafkaConsumer] = None,
        no_stats_secs: float = NO_STATS_REBOOT_SECS,
        all_down_secs: float = ALL_DOWN_REBOOT_SECS,
        cooldown_secs: float = REBOOT_COOLDOWN_SECS,
        wait_after_assign_secs: float = WAIT_AFTER_ASSIGN_SECS,
        # Stuck-with-lag controls
        stuck_with_lag_secs: float = STUCK_WITH_LAG_SECS,
        min_lag_for_stuck: int = MIN_LAG_FOR_STUCK,
        # DI time/sleep
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        use_thread: bool = True,
    ):
        if consumer is not None:
            self._consumer = consumer
        elif brokers is not None:
            self._consumer = KafkaConsumer.create(brokers)
        else:
            raise ValueError("Either brokers or consumer must be provided")

        self._polling_thread = None
        self._stop_event = threading.Event()
        self._messages_callback = None
        self._no_messages_callback = None

        # thresholds
        self._no_stats_secs = float(no_stats_secs)
        self._all_down_secs = float(all_down_secs)
        self._cooldown_secs = float(cooldown_secs)
        self._wait_after_assign_secs = float(wait_after_assign_secs)
        self._stuck_with_lag_secs = float(stuck_with_lag_secs)
        self._min_lag_for_stuck = int(min_lag_for_stuck)

        # time functions
        self._now = now
        self._sleep = sleep

        # polling state
        self._last_no_msg_cb = 0.0
        self._idle_backoff = 0.01
        self._last_deliver_mono = self._now()
        self._last_seen: dict[
            tuple[str, int], int
        ] = {}  # (topic,partition) -> last offset seen
        self._last_pos: dict[
            tuple[str, int], int
        ] = {}  # track positions to detect progress
        self._pos_progressed: bool = False
        self._empty_reads: int = 0

        self._use_thread = use_thread

    def subscribe(
        self, topics: Sequence[str], messages_callback, no_messages_callback=None
    ):
        """
        API-compatibility: name is 'subscribe', but it performs manual assign.
        """
        self.stop_consuming(True)

        self._consumer.unsubscribe()
        self._consumer.subscribe(topics)

        self._messages_callback = messages_callback
        self._no_messages_callback = no_messages_callback

        # reset poller state
        self._last_no_msg_cb = 0.0
        self._idle_backoff = 0.01
        self._last_deliver_mono = self._now()
        self._last_seen.clear()
        self._last_pos.clear()
        self._pos_progressed = False
        self._empty_reads = 0
        self._stop_event.clear()

        if self._use_thread:
            self._polling_thread = createThread(
                f"polling_thread_{int(self._now())}", self._monitor_topics
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

    # --------------------------
    # Lag calculation
    # --------------------------
    def _compute_total_lag(self) -> int:
        """
        total_lag = Σ (high_watermark - position)
        where:
          - high_watermark is the broker's end offset (next produced)
          - position is the consumer's next-to-fetch offset
        Fallbacks:
          - if position unavailable, use last_seen+1 if we have it
          - else use low watermark (earliest available offset)
        Side-effect:
          - sets self._pos_progressed when positions advance
        """
        total_lag = 0
        progressed = False
        try:
            assigned = self._consumer.assignment()
            if not assigned:
                self._pos_progressed = False
                return 0

            # Prefer stats lag if stats are fresh and populated
            if (
                self._consumer.last_stats_age() < 3.0
                and self._consumer._health.stats_by_tp
            ):
                total = 0
                for (t, p), info in self._consumer._health.stats_by_tp.items():
                    lag = int(info.get("lag", 0) or 0)
                    total += max(0, lag)
                self._pos_progressed = False  # no position insight from stats
                session.log.debug("[kafka] total lag from stats: %d", total)
                return int(total)

            # Get current positions in one call (best-effort)
            try:
                with self._consumer._lock:
                    positions = self._consumer._consumer.position(assigned)
            except Exception:
                positions = None

            pos_map: dict[tuple[str, int], int] = {}
            if positions:
                for pos_tp in positions:
                    if pos_tp is None:
                        continue
                    try:
                        key = (pos_tp.topic, pos_tp.partition)
                        pos_val = int(pos_tp.offset)
                        pos_map[key] = pos_val
                        # progress detection
                        if pos_val > self._last_pos.get(key, -1):
                            self._last_pos[key] = pos_val
                            progressed = True
                    except Exception:
                        pass

            for tp in assigned:
                try:
                    low, high = self._consumer._consumer.get_watermark_offsets(tp)
                except Exception:
                    # No signal for this partition this tick
                    continue

                key = (tp.topic, tp.partition)
                # Prefer true consumer position if available
                pos = pos_map.get(key, None)

                if pos is None or pos < 0:
                    # Fall back to our last delivered offset + 1
                    last = self._last_seen.get(key, OFFSET_END)
                    if last != OFFSET_END:
                        pos = int(last) + 1
                    else:
                        # Last resort: earliest available offset
                        pos = int(low)

                lag = max(0, int(high) - int(pos))
                total_lag += lag
        except Exception:
            # Keep watchdogs resilient
            total_lag = 0

        self._pos_progressed = progressed
        session.log.debug("[kafka] total lag computed: %d", total_lag)
        return total_lag

    # --------------------------
    # Main loop
    # --------------------------
    def tick(self):
        now = self._now()

        # 0) Periodic metadata probe for partition changes
        if not self._consumer._pending_reassign:
            self._consumer._maybe_refresh_partitions()

        # 1) Deferred reassign
        if self._consumer._pending_reassign:
            assigned = self._consumer.try_reassign()
            if not assigned:
                self._sleep(0.01)
                return

        # 1.5) Detect lost assignment and request reassign
        if (
            self._consumer._topics
            and not self._consumer.assignment()
            and (now - self._consumer._last_assign_mono) > self._wait_after_assign_secs
        ):
            session.log.warning("[kafka] assignment lost; scheduling reassign")
            self._consumer._pending_reassign = True
            self._sleep(0.01)
            return

        # 2) Watchdogs (cooldown via injected clock)
        since_assign = now - self._consumer._last_assign_mono
        since_reboot_ok = (
            now - self._consumer._last_rebootstrap_mono
        ) >= self._cooldown_secs

        if (
            self._consumer.all_brokers_down_for() > self._all_down_secs
            and since_reboot_ok
            and since_assign > self._wait_after_assign_secs
            and not self._consumer._pending_reassign
        ):
            self._consumer.rebootstrap("all_brokers_down")
            self._sleep(0.01)
            return

        if (
            self._consumer.last_stats_age() > self._no_stats_secs
            and since_reboot_ok
            and since_assign > self._wait_after_assign_secs
            and not self._consumer._pending_reassign
        ):
            self._consumer.rebootstrap("no_stats_heartbeat")
            self._sleep(0.01)
            return

        # 2.5) Lag watchdog (includes position-progress-as-progress)
        total_lag = self._compute_total_lag()
        if self._pos_progressed:
            # treat forward movement as progress (even if we dropped messages)
            self._last_deliver_mono = now

        no_progress_for = now - self._last_deliver_mono
        if since_reboot_ok and since_assign > self._wait_after_assign_secs:
            if (
                total_lag >= self._min_lag_for_stuck
                and no_progress_for > self._stuck_with_lag_secs
                and not self._consumer._pending_reassign
            ):
                self._consumer.rebootstrap("stuck_no_progress_despite_lag")
                self._sleep(0.01)
                return

        # 3) Consume
        msgs = self._consumer.consume_batch(MAX_BATCH_SIZE, timeout_s=0.05)
        deliver: List[Tuple[Tuple[int, int], bytes]] = []
        had_error = False
        for m in msgs:
            if m is None:
                continue
            try:
                err = m.error()
            except Exception:
                err = None
            if err:
                had_error = True
                try:
                    code = err.code()
                    if code == KafkaError._PARTITION_EOF:
                        pass
                    elif code == KafkaError._ALL_BROKERS_DOWN:
                        session.log.warning("[kafka-event] all brokers down (event)")
                    elif code == KafkaError._OFFSET_OUT_OF_RANGE:
                        # Auto-recover per starting_offset policy
                        try:
                            if self._consumer._starting_offset.lower() in (
                                "earliest",
                                "beginning",
                                "smallest",
                            ):
                                self._consumer.seek_to_beginning()
                            else:
                                self._consumer.seek_to_end()
                            session.log.warning(
                                "[kafka] OFFSET_OUT_OF_RANGE: auto-seek executed"
                            )
                            # Treat this as progress to avoid immediate reboot
                            self._last_deliver_mono = self._now()
                        except Exception as e:
                            session.log.warning("[kafka] auto-seek failed: %r", e)
                    else:
                        session.log.warning(
                            "[kafka-msg-error] code=%s name=%s retriable=%s fatal=%s msg=%s",
                            code,
                            err.name(),
                            err.retriable(),
                            err.fatal(),
                            err.str(),
                        )
                except Exception:
                    session.log.warning("[kafka-msg-error] %r", err)
                continue
            try:
                # Track last seen offsets for lag computation
                try:
                    t = m.topic()
                    p = m.partition()
                    o = m.offset()
                    key = (t, p)
                    prev = self._last_seen.get(key, -1)
                    if o is not None:
                        self._last_seen[key] = max(prev, int(o))
                except Exception:
                    pass
                deliver.append((m.timestamp(), m.value()))
            except Exception:
                continue

        if deliver:
            self._idle_backoff = 0.01
            self._last_deliver_mono = now
            self._empty_reads = 0
            if self._messages_callback:
                try:
                    self._messages_callback(deliver)
                except Exception:
                    session.log.error("[kafka] messages_callback raised")
        else:
            # No deliveries this cycle
            self._empty_reads += 1

            # Escalate on repeated empty reads while stats say we have lag
            stats_lag = self._consumer._health.stats_total_lag
            if (
                stats_lag >= self._min_lag_for_stuck
                and self._empty_reads >= 40  # ~2–8s depending on backoff
                and since_reboot_ok
                and since_assign > self._wait_after_assign_secs
                and not self._consumer._pending_reassign
            ):
                self._consumer.rebootstrap("stuck_empty_reads_with_stats_lag")
                self._sleep(0.01)
                return

            if self._no_messages_callback and (now - self._last_no_msg_cb) > 0.1:
                try:
                    self._no_messages_callback()
                except Exception:
                    session.log.error("[kafka] no_messages_callback raised")
                self._last_no_msg_cb = now

            self._idle_backoff = min(
                0.2, self._idle_backoff * (1.5 if not had_error else 1.0)
            )
            self._sleep(self._idle_backoff)

    def _monitor_topics(self):
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as e:
                session.log.error("Exception in KafkaSubscriber loop: %r", e)
                self._sleep(0.5)


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
    import logging

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
