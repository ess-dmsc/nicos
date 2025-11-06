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
STUCK_WITH_LAG_SECS = 8.0
MIN_LAG_FOR_STUCK = 1
PARTITION_PROBE_INTERVAL_SECS = 10.0

ERR_UNKNOWN_TOPIC_OR_PART = getattr(KafkaError, "_UNKNOWN_TOPIC_OR_PART", 3)
ERR_OFFSET_OUT_OF_RANGE = getattr(KafkaError, "_OFFSET_OUT_OF_RANGE", 1)
ERR_ALL_BROKERS_DOWN = getattr(KafkaError, "_ALL_BROKERS_DOWN", -187)
ERR_PARTITION_EOF = getattr(KafkaError, "_PARTITION_EOF", -191)


@dataclass
class _Health:
    """Internal container for health/telemetry derived from librdkafka `stats_cb`.

    Attributes
    ----------
    last_stats_mono:
        Monotonic timestamp (seconds) of the last received stats payload.
    all_down_since:
        Monotonic timestamp when all brokers first appeared DOWN, or None.
    brokers_state:
        Mapping of broker-id/host to string state (e.g. "UP", "DOWN").
    group_coordinator_state:
        Consumer group coordinator state, normalized to upper-case (e.g. "UP").
    stats_total_lag:
        Sum of per-partition lags as reported by stats.
    stats_by_tp:
        Per-topic/partition dictionary with keys like ('topic', part) and
        values including `lag` and optional `fetch_state`.
    """

    last_stats_mono: float = time.monotonic()
    all_down_since: Optional[float] = None
    brokers_state: dict = None
    group_coordinator_state: Optional[str] = None
    stats_total_lag: int = 0
    stats_by_tp: Dict[tuple, dict] = (
        None  # (topic, part) -> {'lag': int, 'fetch_state': str}
    )

    def __post_init__(self):
        """Initialize default mutable fields."""
        if self.brokers_state is None:
            self.brokers_state = {}
        if self.stats_by_tp is None:
            self.stats_by_tp = {}

    def brokers_up(self) -> int:
        """Return the number of brokers currently reported as UP."""
        return sum(1 for s in self.brokers_state.values() if s == "UP")

    def group_coordinator_up(self) -> bool:
        """Return True if the consumer group coordinator is reported as UP."""
        return self.group_coordinator_state == "UP"


class KafkaConsumer:
    """Manual-assign consumer wrapper with robust watchdogs (API compatible)."""

    @staticmethod
    def create(
        brokers: Sequence[str], starting_offset: str = "latest", **options
    ) -> "KafkaConsumer":
        """Factory for :class:`KafkaConsumer` with SASL options injected.

        Parameters
        ----------
        brokers:
            Iterable of broker addresses (e.g. ``["host:9092"]``).
        starting_offset:
            Initial offset policy for new assignments; typically
            ``"earliest"`` or ``"latest"``.
        **options:
            Additional librdkafka configuration entries.

        Returns
        -------
        KafkaConsumer
            A configured consumer wrapper instance.
        """
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
        """Create a consumer wrapper.

        Parameters
        ----------
        brokers:
            Iterable of bootstrap broker endpoints.
        starting_offset:
            Initial offset policy for assignments (``"earliest"``/``"latest"``).
        consumer_factory:
            Callable that receives the merged config dict and returns a
            confluent-kafka Consumer-like object. Used for DI/testing.
        topic_partition_factory:
            Callable used to construct ``TopicPartition`` objects.
        now:
            Monotonic clock function (seconds); used for timers.
        sleep:
            Sleep function; used for backoffs and jitter.
        rand_uniform:
            RNG function taking ``(low, high)`` and returning a float; used for jitter.
        on_rebootstrap:
            Optional callback invoked with a string reason whenever a reboot
            is performed.
        **options:
            Additional librdkafka configuration entries merged into the base
            configuration.
        """
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
            "statistics.interval.ms": 5000,
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

        # After delete+recreate we may need to "prime" fetch with an explicit seek
        self._need_seek_after_assign: bool = False

        self._lock = threading.RLock()

    @staticmethod
    def is_partition_eof(err: object) -> bool:
        """Return True if the error is a PARTITION_EOF event."""
        try:
            return int(getattr(err, "code")()) == ERR_PARTITION_EOF
        except Exception:
            return False

    @staticmethod
    def is_all_brokers_down(err: object) -> bool:
        """Return True if the error indicates ALL_BROKERS_DOWN."""
        try:
            return int(getattr(err, "code")()) == ERR_ALL_BROKERS_DOWN
        except Exception:
            return False

    @staticmethod
    def is_offset_out_of_range(err: object) -> bool:
        """Return True if the error indicates OFFSET_OUT_OF_RANGE."""
        try:
            return int(getattr(err, "code")()) == ERR_OFFSET_OUT_OF_RANGE
        except Exception:
            return False

    @staticmethod
    def is_unknown_topic_or_partition(err: object) -> bool:
        """Return True if the error indicates an unknown topic or partition."""
        try:
            code = int(getattr(err, "code")())
            if code == ERR_UNKNOWN_TOPIC_OR_PART:
                return True
            name = str(getattr(err, "name")() or "")
            return name in ("UNKNOWN_TOPIC_OR_PART", "_UNKNOWN_PARTITION")
        except Exception:
            return False

    def brokers_up(self) -> int:
        """Return the number of brokers that are currently reported as UP.

        Returns
        -------
        int
            Count of brokers in ``"UP"`` state according to last stats.
        """
        return self._health.brokers_up()

    def all_brokers_down_for(self) -> float:
        """Return the duration (seconds) that all brokers have been DOWN.

        Returns
        -------
        float
            Seconds since all brokers down, or ``0.0`` if not currently all DOWN.
        """
        if self._health.all_down_since is None:
            return 0.0
        return max(0.0, self._now() - self._health.all_down_since)

    def last_stats_age(self) -> float:
        """Return the age (seconds) of the last received statistics payload.

        Returns
        -------
        float
            Age in seconds (monotonic), ``0.0`` if called at the same instant.
        """
        return max(0.0, self._now() - self._health.last_stats_mono)

    def _can_fetch_metadata(
        self, topic: Optional[str] = None, timeout_s: float = 1.0
    ) -> bool:
        """Best-effort probe to see if metadata is retrievable."""
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
                    session.log.warning(
                        "[kafka] meta probe: %s partitions changed %s -> %s",
                        t,
                        self._partitions_known.get(t),
                        count,
                    )
                    self._partitions_known[t] = count
                    changed = True
            if changed:
                session.log.warning(
                    "[kafka] partition count change detected; scheduling reassign"
                )
                self._pending_reassign = True
        except Exception as e:
            session.log.debug("[kafka] metadata probe failed: %r", e)

    # Public facade for the periodic probe (keeps subscriber off privates)
    def refresh_partitions_if_stale(
        self, interval_s: float = PARTITION_PROBE_INTERVAL_SECS
    ) -> None:
        """Trigger a best-effort metadata probe if the last probe is stale.

        Parameters
        ----------
        interval_s:
            Minimum interval between metadata probes (seconds).
        """
        self._maybe_refresh_partitions(interval_s)

    # ---------- try_reassign refactor ----------
    def try_reassign(self) -> bool:
        """Attempt to (re)assign partitions for the current set of topics.

        This method:
        - Fetches cluster metadata,
        - Verifies each subscribed topic exists with at least one partition,
        - Assigns all discovered topic/partition pairs,
        - Optionally resumes the assignment (best-effort),
        - Performs a post-assign seek when flagged,
        - "Kicks" the consumer to establish fetch sessions.

        Returns
        -------
        bool
            ``True`` if a new assignment was applied (or there are no topics);
            ``False`` if metadata isn't ready yet or assignment was deferred.
        """
        if not self._topics:
            self._pending_reassign = False
            return True

        if self._should_backoff_reassign():
            return False

        try:
            with self._lock:
                self._safe_unassign_current()
                md = self._fetch_cluster_metadata()

                ok, topic_partitions = self._build_assignment_from_metadata(md)
                if not ok:
                    return False

                self._apply_assignment_and_maybe_resume(topic_partitions)

            self._post_assignment_housekeeping(
                topic_partitions, context="post-reassign"
            )
            return True

        except KafkaException as exc:
            session.log.debug("[kafka] metadata not ready yet during reassign: %r", exc)
            return False

    def _should_backoff_reassign(self) -> bool:
        """Return True if brokers appear down and metadata fetch also fails."""
        if self.brokers_up() == 0 and not self._can_fetch_metadata(None, timeout_s=0.5):
            session.log.debug("[kafka] try_reassign: brokers down & no metadata yet")
            return True
        return False

    def _safe_unassign_current(self) -> None:
        """Best-effort unassign to flush any stale fetch state."""
        try:
            session.log.debug("[kafka] try_reassign: unassigning current assignment")
            self._consumer.unassign()
        except Exception:
            pass

    def _fetch_cluster_metadata(self):
        """Return cluster-wide metadata with a short timeout."""
        return self._consumer.list_topics(None, timeout=2.0)

    def _build_assignment_from_metadata(self, md) -> Tuple[bool, List[TopicPartition]]:
        """Collect TopicPartition objects for all subscribed topics.

        Returns
        -------
        (ok, partitions)
            ok=False indicates metadata not yet ready (keep retrying).
        """
        topic_partitions: List[TopicPartition] = []
        for topic_name in self._topics:
            tmeta = md.topics.get(topic_name)
            if tmeta is None:
                session.log.debug(
                    "[kafka] try_reassign: topic %s not in metadata yet", topic_name
                )
                return False, []
            if getattr(tmeta, "error", None) is not None:
                session.log.debug(
                    "[kafka] try_reassign: topic %s metadata error=%r (wait)",
                    topic_name,
                    tmeta.error,
                )
                return False, []

            parts = list(getattr(tmeta, "partitions", {}).keys())
            if not parts:
                session.log.debug(
                    "[kafka] try_reassign: topic %s has no partitions yet (wait)",
                    topic_name,
                )
                return False, []

            for p in parts:
                topic_partitions.append(self._tp_factory(topic_name, p))
            self._partitions_known[topic_name] = len(parts)
        return True, topic_partitions

    def _apply_assignment_and_maybe_resume(
        self, partitions: Sequence[TopicPartition]
    ) -> None:
        """Assign partitions and best-effort resume."""
        session.log.debug(
            "[kafka] try_reassign: assigning %s",
            [(tp.topic, tp.partition) for tp in partitions],
        )
        self._consumer.assign(list(partitions))
        try:
            self._consumer.resume(list(partitions))  # type: ignore[attr-defined]
        except Exception:
            pass

    def _post_assignment_housekeeping(
        self, partitions: Sequence[TopicPartition], *, context: str
    ) -> None:
        """Finalize internal state and perform post-assign actions."""
        self._last_assignment = list(partitions)
        self._pending_reassign = False
        self._last_assign_mono = self._now()
        session.log.debug(
            "[kafka] (re)assigned partitions: %s",
            [(tp.topic, tp.partition) for tp in partitions],
        )
        self._maybe_post_assign_seek()
        self.kick(times=6 if context == "post-reassign" else 2)
        self._log_assignment_debug(context)

    def _on_error(self, err):
        """Internal error callback: logs details and may trigger rebootstrap."""
        try:
            code = err.code()
            name = str(err.name() or "")
            session.log.warning(
                "[kafka-error] code=%s name=%s fatal=%s retriable=%s msg=%s",
                code,
                name,
                err.fatal(),
                err.retriable(),
                err.str(),
            )

            if self.is_unknown_topic_or_partition(err):
                session.log.warning(
                    "[kafka] error-cb: topic/partition missing; scheduling reassign+seek"
                )
                self.schedule_reassign()
                self.schedule_seek_after_assign()

            if err.fatal():
                if self.reboot_cooldown_passed(REBOOT_COOLDOWN_SECS):
                    self.rebootstrap("fatal_error:%s" % name)
        except Exception:
            session.log.warning("[kafka-error] %r", err)

    def _on_stats(self, stats_json: str):
        """Internal stats callback: parse JSON and update health metrics."""
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

    def subscribe(self, topics: Sequence[str]):
        """Assign all partitions of the given topics.

        Parameters
        ----------
        topics:
            Sequence of topic names to consume (manual assignment).

        Raises
        ------
        ConfigurationError
            If metadata cannot be obtained or a provided topic is missing/errored.
        """
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
            session.log.debug(
                "[kafka] subscribe: assigning %s",
                [(tp.topic, tp.partition) for tp in topic_partitions],
            )
            self._consumer.assign(topic_partitions)

        self._topics = list(topics)
        self._last_assignment = list(topic_partitions)
        self._pending_reassign = False
        self._last_assign_mono = self._now()
        session.log.debug(
            "[kafka] assigned partitions: %s",
            [(tp.topic, tp.partition) for tp in topic_partitions],
        )

        self._maybe_post_assign_seek()
        self.kick(times=2)
        self._log_assignment_debug("post-subscribe")

    def rebootstrap(self, reason: str = ""):
        """Close and recreate the underlying consumer and (re)subscribe.

        Parameters
        ----------
        reason:
            A short string describing why the reboot is happening; forwarded
            to the optional `on_rebootstrap` callback.

        Notes
        -----
        - Applies a short random jitter before re-creating the consumer.
        - If re-subscription fails, sets a pending reassign flag to be handled
          by the higher-level subscriber.
        """
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
                session.log.debug("[kafka-rebootstrap] closing consumer")
                self._consumer.close()
        except Exception as e:
            session.log.debug("[kafka-rebootstrap] close() error ignored: %r", e)

        with self._lock:
            session.log.debug("[kafka-rebootstrap] creating new consumer")
            self._consumer = self._consumer_factory(self._conf_effective)

        reassigned_ok = False
        if self._topics:
            try:
                self.subscribe(self._topics)
                reassigned_ok = True
                session.log.debug(
                    "[kafka-rebootstrap] re-subscribed to topics=%s", self._topics
                )
            except Exception as e:
                session.log.warning("[kafka-rebootstrap] re-subscribe failed: %r", e)

        self._health = _Health()
        self._pending_reassign = not reassigned_ok and bool(self._topics)
        self._last_rebootstrap_mono = self._now()

    def unsubscribe(self):
        """Best-effort unsubscribe from all assignments."""
        with self._lock:
            try:
                session.log.debug("[kafka] unsubscribe()")
                self._consumer.unsubscribe()
            except Exception:
                pass

    def poll(self, timeout_ms: int = 5):
        """Poll a single message.

        Parameters
        ----------
        timeout_ms:
            Maximum time to block waiting for a message, milliseconds.

        Returns
        -------
        object | None
            A message-like object from the underlying consumer, or ``None`` if
            no message is available.
        """
        with self._lock:
            return self._consumer.poll(timeout_ms / 1000.0)

    def kick(self, times: int = 1):
        """Poll(0) a few times to nudge librdkafka to establish fetch sessions.

        Parameters
        ----------
        times:
            Number of zero-timeout polls to perform (minimum 1).
        """
        for _ in range(max(1, int(times))):
            try:
                _ = self.poll(0)
            except Exception as e:
                session.log.debug("[kafka] kick poll(0) failed: %r", e)

    def consume_batch(self, max_messages: int = MAX_BATCH_SIZE, timeout_s: float = 0.2):
        """Consume up to ``max_messages`` messages.

        Parameters
        ----------
        max_messages:
            Maximum number of messages to return. ``<=0`` returns an empty list.
        timeout_s:
            Per-call timeout in seconds for the underlying consumer.

        Returns
        -------
        list
            List of message-like objects (possibly empty).
        """
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
        """Close the underlying consumer (idempotent)."""
        with self._lock:
            try:
                session.log.debug("[kafka] close()")
                self._consumer.close()
            except Exception:
                pass

    def topics(self, timeout_s: float = 5) -> List[str]:
        """Return the list of known topic names.

        Parameters
        ----------
        timeout_s:
            Metadata request timeout in seconds.

        Returns
        -------
        list[str]
            Topic names from the broker metadata.
        """
        with self._lock:
            return list(self._consumer.list_topics(timeout=timeout_s).topics)

    def seek(self, topic_name: str, partition: int, offset: int, timeout_s: float = 5):
        """Seek a single topic/partition to a specific offset.

        Parameters
        ----------
        topic_name:
            Topic to seek.
        partition:
            Partition id to seek.
        offset:
            Target offset (or ``OFFSET_BEGINNING``/``OFFSET_END``).
        timeout_s:
            Maximum time in seconds to complete the seek (with retries).
        """
        tp = self._tp_factory(topic_name, partition, offset)
        self._seek([tp], timeout_s)

    def _seek(self, partitions: Sequence[TopicPartition], timeout_s: float):
        """Internal multi-partition seek with retries until the deadline."""
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
                    session.log.debug(
                        "[kafka] seek() ok topic=%s part=%d off=%s", topic, part, off
                    )
                    done_now.append((topic, part, off))
                except KafkaException as e:
                    last_err = e
                    session.log.debug("[kafka] seek() retry due to: %r", e)
                    self._sleep(0.1)
            for item in done_now:
                remaining.discard(item)
        if remaining:
            raise RuntimeError(
                f"failed to seek offsets for: {sorted(remaining)}; last_err={last_err!r}"
            )

    def assignment(self) -> List[TopicPartition]:
        """Return the current partition assignment.

        Returns
        -------
        list[TopicPartition]
            A list of assigned topic/partitions (possibly empty).
        """
        with self._lock:
            return self._consumer.assignment()

    def seek_to_end(self, timeout_s: float = 5):
        """Seek all assigned partitions to ``OFFSET_END``."""
        with self._lock:
            partitions = self._consumer.assignment()
        for tp in partitions:
            tp.offset = OFFSET_END
        self._seek(partitions, timeout_s)

    def seek_to_beginning(self, timeout_s: float = 5):
        """Seek all assigned partitions to ``OFFSET_BEGINNING``."""
        with self._lock:
            partitions = self._consumer.assignment()
        for tp in partitions:
            tp.offset = OFFSET_BEGINNING
        self._seek(partitions, timeout_s)

    def unassign(self):
        """Expose unassign for testing/manual flows (best-effort)."""
        with self._lock:
            try:
                self._consumer.unassign()
            except Exception:
                pass

    def positions(
        self, partitions: Sequence[TopicPartition]
    ) -> Optional[List[TopicPartition]]:
        """Return the current positions for the given partitions.

        This is a thread-safe wrapper around the underlying consumer's
        `position()` call. On platforms or test doubles that do not implement
        `position()`, this method returns ``None`` rather than raising.

        Parameters
        ----------
        partitions:
            Sequence of topic/partitions for which to query positions.

        Returns
        -------
        list[TopicPartition] | None
            The position-bearing `TopicPartition` instances corresponding to
            ``partitions`` when supported; otherwise ``None``.
        """
        with self._lock:
            try:
                return self._consumer.position(list(partitions))  # type: ignore[attr-defined]
            except Exception:
                try:
                    return self._consumer.position(list(partitions))  # type: ignore[no-any-return]
                except Exception:
                    return None

    def watermark_offsets(
        self, tp: TopicPartition, timeout_s: float = 5.0
    ) -> Tuple[Optional[int], Optional[int]]:
        """Return low/high watermark offsets for a partition.

        Parameters
        ----------
        tp:
            Topic/partition to inspect.
        timeout_s:
            Maximum time in seconds to wait (best effort).

        Returns
        -------
        tuple[int | None, int | None]
            A tuple of ``(low, high)`` offsets, or ``(None, None)`` if the call
            is not supported or fails.
        """
        with self._lock:
            try:
                low, high = self._consumer.get_watermark_offsets(tp, timeout=timeout_s)  # type: ignore[attr-defined]
                return int(low), int(high)
            except Exception:
                try:
                    low, high = self._consumer.get_watermark_offsets(tp)  # type: ignore[no-any-return]
                    return int(low), int(high)
                except Exception:
                    return None, None

    def stats_total_lag(self) -> int:
        """Return the most recent total lag from the stats callback."""
        try:
            return int(self._health.stats_total_lag or 0)
        except Exception:
            return 0

    def stats_by_tp(self) -> Dict[Tuple[str, int], Dict[str, object]]:
        """Return a shallow copy of per-partition stats from the stats callback.

        Returns
        -------
        dict[tuple[str, int], dict[str, object]]
            Mapping from (topic, partition) to a dictionary containing at least
            ``{\"lag\": int}`` and optionally other fields like ``\"fetch_state\"``.
        """
        try:
            out: Dict[Tuple[str, int], Dict[str, object]] = {}
            for (t, p), info in (self._health.stats_by_tp or {}).items():
                out[(str(t), int(p))] = dict(info or {})
            return out
        except Exception:
            return {}

    def group_coordinator_state(self) -> Optional[str]:
        """Return the last known consumer-group coordinator state."""
        state = self._health.group_coordinator_state
        return str(state).upper() if state is not None else None

    def schedule_reassign(self) -> None:
        """Mark that a partition (re)assignment should be attempted soon."""
        self._pending_reassign = True

    def clear_reassign(self) -> None:
        """Clear the reassign-pending marker."""
        self._pending_reassign = False

    def is_reassign_pending(self) -> bool:
        """Return True if a (re)assignment has been scheduled."""
        return bool(self._pending_reassign)

    def subscribed_topics(self) -> List[str]:
        """Return the topics currently subscribed/assigned (manual-assign)."""
        return list(self._topics)

    def time_since_last_assign(self) -> float:
        """Return seconds since the last (re)assignment, or ``0.0`` if never."""
        if self._last_assign_mono <= 0.0:
            return 0.0
        return max(0.0, self._now() - self._last_assign_mono)

    def time_since_last_rebootstrap(self) -> float:
        """Return seconds since the last rebootstrap, or ``inf`` if never."""
        if self._last_rebootstrap_mono <= 0.0:
            return float("inf")
        return max(0.0, self._now() - self._last_rebootstrap_mono)

    def reboot_cooldown_passed(self, cooldown_secs: float) -> bool:
        """Return True if at least ``cooldown_secs`` have elapsed since reboot."""
        return self.time_since_last_rebootstrap() >= float(cooldown_secs)

    def schedule_seek_after_assign(self, policy: Optional[str] = None) -> None:
        """Schedule a one-time post-(re)assignment seek.

        Parameters
        ----------
        policy:
            Optional policy override: e.g. ``"earliest"`` or ``"latest"``.
            If provided, it temporarily overrides the starting offset policy
            used by the post-assign seek.
        """
        if policy:
            self._starting_offset = str(policy)
        self._need_seek_after_assign = True

    def _log_assignment_debug(self, prefix: str):
        """Log useful debug information about the current assignment."""
        try:
            with self._lock:
                assigned = self._consumer.assignment()
                if not assigned:
                    session.log.debug("[kafka][%s] no assignment", prefix)
                    return
                positions = None
                try:
                    positions = self._consumer.position(assigned)  # type: ignore[attr-defined]
                except Exception:
                    try:
                        positions = self._consumer.position(
                            assigned
                        )  # may not exist on stub
                    except Exception:
                        positions = None

                pos_map = {}
                if positions:
                    for pt in positions:
                        try:
                            pos_map[(pt.topic, pt.partition)] = int(pt.offset)
                        except Exception:
                            pass

                for tp in assigned:
                    try:
                        low, high = self._consumer.get_watermark_offsets(tp)  # type: ignore[attr-defined]
                    except Exception:
                        try:
                            low, high = self._consumer.get_watermark_offsets(
                                tp
                            )  # may not exist on stub
                        except Exception:
                            low, high = (None, None)
                    pos = pos_map.get((tp.topic, tp.partition))
                    stats = self._health.stats_by_tp.get((tp.topic, tp.partition), {})
                    session.log.debug(
                        "[kafka][%s] tp=%s[%d] pos=%s low=%s high=%s statsLag=%s fetch=%s",
                        prefix,
                        tp.topic,
                        tp.partition,
                        pos,
                        low,
                        high,
                        stats.get("lag"),
                        stats.get("fetch_state"),
                    )
        except Exception as e:
            session.log.debug("[kafka] _log_assignment_debug failed: %r", e)

    def _maybe_post_assign_seek(self):
        """If flagged, perform a one-time seek after (re)assignment."""
        if not self._need_seek_after_assign:
            return
        try:
            if str(self._starting_offset).lower() in (
                "earliest",
                "beginning",
                "smallest",
            ):
                self.seek_to_beginning()
                session.log.debug(
                    "[kafka] post-assign seek to beginning executed after topic recreation"
                )
            else:
                self.seek_to_end()
                session.log.debug(
                    "[kafka] post-assign seek to end executed after topic recreation"
                )
            session.log.warning(
                "[kafka] post-assign seek executed after topic recreation"
            )
        except Exception as e:
            session.log.warning("[kafka] post-assign seek failed: %r", e)
        finally:
            self._need_seek_after_assign = False


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
        stuck_with_lag_secs: float = STUCK_WITH_LAG_SECS,
        min_lag_for_stuck: int = MIN_LAG_FOR_STUCK,
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        use_thread: bool = True,
    ):
        """Create a :class:`KafkaSubscriber`.

        Parameters
        ----------
        brokers:
            Optional list of broker addresses; used if `consumer` is not provided.
        consumer:
            Pre-built :class:`KafkaConsumer` instance for dependency injection.
        no_stats_secs:
            Threshold (seconds) after which missing stats triggers a reboot.
        all_down_secs:
            Threshold (seconds) after which brokers DOWN triggers a reboot.
        cooldown_secs:
            Minimum time between reboots.
        wait_after_assign_secs:
            Grace period after assignment before watchdogs can trigger.
        stuck_with_lag_secs:
            Time without deliveries (with lag present) that triggers a reboot.
        min_lag_for_stuck:
            Minimum lag required to consider the consumer "stuck".
        now:
            Monotonic clock function (seconds).
        sleep:
            Sleep function.
        use_thread:
            If True, start a background thread; otherwise call :meth:`tick` manually.
        """
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

        self._no_stats_secs = float(no_stats_secs)
        self._all_down_secs = float(all_down_secs)
        self._cooldown_secs = float(cooldown_secs)
        self._wait_after_assign_secs = float(wait_after_assign_secs)
        self._stuck_with_lag_secs = float(stuck_with_lag_secs)
        self._min_lag_for_stuck = int(min_lag_for_stuck)

        self._now = now
        self._sleep = sleep

        self._last_no_msg_cb = 0.0
        self._idle_backoff = 0.01
        self._last_deliver_mono = self._now()
        self._last_seen: dict[tuple[str, int], int] = {}
        self._last_pos: dict[tuple[str, int], int] = {}
        self._pos_progressed: bool = False
        self._empty_reads: int = 0

        self._use_thread = use_thread

    def subscribe(
        self, topics: Sequence[str], messages_callback, no_messages_callback=None
    ):
        """Subscribe to topics and start (or prepare) the polling loop.

        Parameters
        ----------
        topics:
            Sequence of topic names to consume from.
        messages_callback:
            Callable that receives a list of ``((ts_type, ts_val), value_bytes)`` tuples.
        no_messages_callback:
            Optional callable invoked periodically while idle.

        Notes
        -----
        If ``use_thread`` was True during construction, this also spawns the
        background polling thread. Otherwise, call :meth:`tick` repeatedly.
        """
        self.stop_consuming(True)

        self._consumer.unsubscribe()
        self._consumer.subscribe(topics)

        self._messages_callback = messages_callback
        self._no_messages_callback = no_messages_callback

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
        """Signal the polling loop to stop; optionally wait for thread join.

        Parameters
        ----------
        wait_for_join:
            If True, block until the background thread exits (if running).
        """
        self._stop_event.set()
        if wait_for_join and self._polling_thread:
            self._polling_thread.join()

    def close(self):
        """Stop consuming and close the underlying consumer."""
        self.stop_consuming(True)
        self._consumer.close()

    @property
    def consumer(self) -> KafkaConsumer:
        """Access the underlying :class:`KafkaConsumer` instance."""
        return self._consumer

    def _compute_total_lag(self) -> int:
        """Compute total lag across the current assignment.

        Prefers stats-based lag if recent and complete; otherwise falls back to
        watermark- and position-based estimation via the consumer abstraction.

        Returns
        -------
        int
            Aggregate lag (non-negative integer).
        """
        try:
            assigned = self._consumer.assignment()
            if not assigned:
                self._pos_progressed = False
                session.log.debug("[kafka] lag: no assignment -> 0")
                return 0

            stats_total = self._try_stats_lag(assigned)
            if stats_total is not None:
                self._pos_progressed = False
                session.log.debug("[kafka] total lag from stats: %d", stats_total)
                return stats_total

            progressed, pos_map = self._build_position_map(assigned)
            total_from_wm = self._lag_from_watermarks(assigned, pos_map)
            self._pos_progressed = progressed
            session.log.debug(
                "[kafka] total lag computed: %d (progressed=%s)",
                total_from_wm,
                progressed,
            )
            return total_from_wm

        except Exception as e:
            session.log.debug("[kafka] lag compute failed: %r -> assuming 0", e)
            self._pos_progressed = False
            return 0

    def _try_stats_lag(self, assigned: Sequence[TopicPartition]) -> Optional[int]:
        """Return total lag from stats if fresh and fully covering the assignment."""
        stats_age = self._consumer.last_stats_age()
        stats_map = self._consumer.stats_by_tp()
        if not (stats_age < 3.0 and stats_map):
            return None

        coverage = all((tp.topic, tp.partition) in stats_map for tp in assigned)
        session.log.debug(
            "[kafka] lag: using stats? age=%.3fs coverage=%s", stats_age, coverage
        )
        if not coverage:
            return None

        total = 0
        for tp in assigned:
            info = stats_map.get((tp.topic, tp.partition), {})
            lag_val = int(info.get("lag", 0) or 0)  # type: ignore[arg-type]
            total += max(0, lag_val)
            session.log.debug(
                "[kafka] lag(stats) tp=%s[%d] lag=%d fetch_state=%s",
                tp.topic,
                tp.partition,
                lag_val,
                info.get("fetch_state"),
            )
        return int(total)

    def _build_position_map(
        self, assigned: Sequence[TopicPartition]
    ) -> Tuple[bool, Dict[Tuple[str, int], int]]:
        """Build a map of current positions and report whether progress occurred."""
        positions = self._consumer.positions(assigned)
        pos_map: Dict[Tuple[str, int], int] = {}
        progressed = False

        if not positions:
            return progressed, pos_map

        for pos_tp in positions:
            if pos_tp is None:
                continue
            try:
                key = (pos_tp.topic, pos_tp.partition)
                pos_val = int(pos_tp.offset)
                pos_map[key] = pos_val
                if pos_val > self._last_pos.get(key, -1):
                    self._last_pos[key] = pos_val
                    progressed = True
            except Exception:
                pass
        return progressed, pos_map

    def _lag_from_watermarks(
        self, assigned: Sequence[TopicPartition], pos_map: Dict[Tuple[str, int], int]
    ) -> int:
        """Compute lag using watermarks and the provided position map."""
        total_lag = 0
        for tp in assigned:
            low, high = self._consumer.watermark_offsets(tp)
            if low is None or high is None:
                session.log.debug(
                    "[kafka] lag: no watermarks for %s[%d] this tick",
                    tp.topic,
                    tp.partition,
                )
                continue

            key = (tp.topic, tp.partition)
            pos = pos_map.get(key, None)
            if pos is None or pos < 0:
                last = self._last_seen.get(key, OFFSET_END)
                pos = (int(last) + 1) if last != OFFSET_END else int(low)

            lag = max(0, int(high) - int(pos))
            total_lag += lag
            session.log.debug(
                "[kafka] lag(wm) tp=%s[%d] low=%s high=%s pos=%s lag=%s",
                tp.topic,
                tp.partition,
                low,
                high,
                pos,
                lag,
            )
        return total_lag

    def _periodic_partition_probe(self):
        """Occasionally probe metadata to detect partition-count changes."""
        if not self._consumer.is_reassign_pending():
            self._consumer.refresh_partitions_if_stale()

    def _handle_pending_reassign(self) -> bool:
        """If a reassign is pending, try it and possibly sleep/return early."""
        if self._consumer.is_reassign_pending():
            assigned = self._consumer.try_reassign()
            if not assigned:
                session.log.debug(
                    "[kafka] tick: pending_reassign not ready, sleeping 1s"
                )
                self._sleep(1.0)
                return True
        return False

    def _handle_lost_assignment(self, now: float) -> bool:
        """Detect lost assignment after grace and schedule a reassign."""
        if (
            self._consumer.subscribed_topics()
            and not self._consumer.assignment()
            and self._consumer.time_since_last_assign() > self._wait_after_assign_secs
        ):
            session.log.warning("[kafka] assignment lost; scheduling reassign")
            self._consumer.schedule_reassign()
            self._sleep(0.01)
            return True
        return False

    def _timers(self, now: float) -> Tuple[float, bool]:
        """Compute time since last assign and whether reboot cooldown passed."""
        since_assign = self._consumer.time_since_last_assign()
        since_reboot_ok = self._consumer.reboot_cooldown_passed(self._cooldown_secs)
        return since_assign, since_reboot_ok

    def _watchdog_all_down(self, since_assign: float, since_reboot_ok: bool) -> bool:
        """Rebootstrap if all brokers have been DOWN for too long."""
        if (
            self._consumer.all_brokers_down_for() > self._all_down_secs
            and since_reboot_ok
            and since_assign > self._wait_after_assign_secs
            and not self._consumer.is_reassign_pending()
        ):
            session.log.warning("[kafka] watchdog: all_brokers_down -> rebootstrap")
            self._consumer.rebootstrap("all_brokers_down")
            self._sleep(0.01)
            return True
        return False

    def _watchdog_no_stats(self, since_assign: float, since_reboot_ok: bool) -> bool:
        """Rebootstrap if stats have not arrived within the configured window."""
        if (
            self._consumer.last_stats_age() > self._no_stats_secs
            and since_reboot_ok
            and since_assign > self._wait_after_assign_secs
            and not self._consumer.is_reassign_pending()
        ):
            session.log.warning(
                "[kafka] watchdog: no_stats age=%.3fs > %.3fs -> rebootstrap",
                self._consumer.last_stats_age(),
                self._no_stats_secs,
            )
            self._consumer.rebootstrap("no_stats_heartbeat")
            self._sleep(0.01)
            return True
        return False

    def _watchdog_stuck_with_lag(
        self, total_lag: int, now: float, since_assign: float, since_reboot_ok: bool
    ) -> bool:
        """Rebootstrap if there is lag and no progress for a sustained period."""
        if since_reboot_ok and since_assign > self._wait_after_assign_secs:
            no_progress_for = now - self._last_deliver_mono
            if (
                total_lag >= self._min_lag_for_stuck
                and no_progress_for > self._stuck_with_lag_secs
                and not self._consumer.is_reassign_pending()
            ):
                session.log.warning(
                    "[kafka] watchdog: stuck w/ lag total=%d no_progress_for=%.3fs -> rebootstrap",
                    total_lag,
                    no_progress_for,
                )
                self._consumer.rebootstrap("stuck_no_progress_despite_lag")
                self._sleep(0.01)
                return True
        return False

    def _handle_message_error(self, err) -> None:
        """Process a per-message error; may seek or schedule reassign."""
        try:
            if KafkaConsumer.is_partition_eof(err):
                session.log.debug("[kafka] msg-error: EOF")
                return
            if KafkaConsumer.is_all_brokers_down(err):
                session.log.warning("[kafka-event] all brokers down (event)")
            elif KafkaConsumer.is_offset_out_of_range(err):
                try:
                    if str(
                        self._consumer._starting_offset
                    ).lower() in (  # uses configured policy
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
                    self._consumer.kick(times=2)
                    self._last_deliver_mono = self._now()
                except Exception as e:
                    session.log.warning("[kafka] auto-seek failed: %r", e)
            elif KafkaConsumer.is_unknown_topic_or_partition(err):
                session.log.warning(
                    "[kafka] msg error: topic/partition missing; scheduling reassign+seek"
                )
                self._consumer.schedule_reassign()
                self._consumer.schedule_seek_after_assign()
            else:
                try:
                    code = err.code()
                    name = str(err.name() or "")
                    session.log.warning(
                        "[kafka-msg-error] code=%s name=%s retriable=%s fatal=%s msg=%s",
                        code,
                        name,
                        err.retriable(),
                        err.fatal(),
                        err.str(),
                    )
                except Exception:
                    session.log.warning("[kafka-msg-error] %r", err)
        except Exception:
            session.log.warning("[kafka-msg-error] %r", err)

    def _track_last_seen(self, msg) -> None:
        """Update the 'last seen' offset for the message's topic/partition."""
        try:
            t = msg.topic()
            p = msg.partition()
            o = msg.offset()
            key = (t, p)
            prev = self._last_seen.get(key, -1)
            if o is not None:
                self._last_seen[key] = max(prev, int(o))
            session.log.debug(
                "[kafka] track: last_seen[%s,%d]=%s (prev=%s)",
                t,
                p,
                self._last_seen.get(key),
                prev,
            )
        except Exception:
            pass

    def _consume_and_dispatch(
        self, now: float, since_assign: float, since_reboot_ok: bool
    ) -> bool:
        """Consume a batch and dispatch to callbacks; handle idle behavior.

        Returns
        -------
        bool
            True if a watchdog action (rebootstrap) was taken and the caller
            should return early; False otherwise.
        """
        msgs = self._consumer.consume_batch(MAX_BATCH_SIZE, timeout_s=0.05)
        deliver, had_error = self._extract_delivery_batch(msgs)

        if deliver:
            self._handle_delivery(deliver, now)
            return False

        return self._handle_idle(had_error, now, since_assign, since_reboot_ok)

    def _extract_delivery_batch(
        self, msgs: Sequence[object]
    ) -> Tuple[List[Tuple[Tuple[int, int], bytes]], bool]:
        """Build the delivery list from raw messages and perform error handling."""
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
                self._handle_message_error(err)
                continue

            try:
                self._track_last_seen(m)
                deliver.append((m.timestamp(), m.value()))
            except Exception:
                continue

        return deliver, had_error

    def _handle_delivery(
        self, deliver: List[Tuple[Tuple[int, int], bytes]], now: float
    ) -> None:
        """Update state and dispatch a non-empty delivery batch."""
        self._idle_backoff = 0.01
        self._last_deliver_mono = now
        self._empty_reads = 0
        session.log.debug("[kafka] deliver: n=%d", len(deliver))
        if self._messages_callback:
            try:
                self._messages_callback(deliver)
            except Exception:
                session.log.error("[kafka] messages_callback raised")

    def _handle_idle(
        self, had_error: bool, now: float, since_assign: float, since_reboot_ok: bool
    ) -> bool:
        """Handle the idle path (no deliveries); may trigger rebootstrap."""
        self._empty_reads += 1
        stats_lag = self._consumer.stats_total_lag()

        session.log.debug(
            "[kafka] idle: empty_reads=%d idle_backoff=%.3f stats_lag=%d last_stats_age=%.3f pending_reassign=%s brokers_up=%d cgrp_up=%s",
            self._empty_reads,
            self._idle_backoff,
            stats_lag,
            self._consumer.last_stats_age(),
            self._consumer.is_reassign_pending(),
            self._consumer.brokers_up(),
            self._consumer.group_coordinator_state(),
        )

        if (
            stats_lag >= self._min_lag_for_stuck
            and self._empty_reads >= 40
            and since_reboot_ok
            and since_assign > self._wait_after_assign_secs
            and not self._consumer.is_reassign_pending()
        ):
            session.log.warning(
                "[kafka] watchdog: empty reads while stats lag=%d -> rebootstrap",
                stats_lag,
            )
            self._consumer.rebootstrap("stuck_empty_reads_with_stats_lag")
            self._sleep(0.01)
            return True

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
        return False

    # ---------- Main loop ----------
    def tick(self):
        """Execute a single iteration of the subscriber state machine."""
        now = self._now()

        self._periodic_partition_probe()

        if self._handle_pending_reassign():
            return

        if self._handle_lost_assignment(now):
            return

        since_assign, since_reboot_ok = self._timers(now)

        if self._watchdog_all_down(since_assign, since_reboot_ok):
            return

        if self._watchdog_no_stats(since_assign, since_reboot_ok):
            return

        total_lag = self._compute_total_lag()
        if self._pos_progressed:
            self._last_deliver_mono = now

        if self._consume_and_dispatch(now, since_assign, since_reboot_ok):
            return

        if self._watchdog_stuck_with_lag(total_lag, now, since_assign, since_reboot_ok):
            return

    def _monitor_topics(self):
        """Background thread target that repeatedly calls :meth:`tick`."""
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as e:
                session.log.error("Exception in KafkaSubscriber loop: %r", e)
                self._sleep(0.5)


if __name__ == "__main__":
    # Simple test / demo, make sure you have a local Kafka broker running
    # with a topic "data_topic" producing some data.
    def print_messages(msgs):
        """Demo callback that prints message timestamps and lengths."""
        for ts, val in msgs:
            ttype, tval = ts
            print(f"msg ts={ttype}:{tval} len={len(val) if val is not None else 0}")

    def print_no_messages():
        """Demo no-messages callback (no-op)."""
        pass

    def create_sasl_config():
        """Demo SASL config provider (no-op)."""
        return {}

    # override logging for local testing
    import logging

    class session:
        """Demo session logger shim."""

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
