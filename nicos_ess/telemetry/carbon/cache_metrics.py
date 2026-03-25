"""Translate selected collector cache updates into Carbon metrics."""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from collections.abc import Callable
from threading import Condition, Thread

from nicos.core import status
from nicos.protocols.cache import cache_load
from nicos_ess.telemetry.carbon.paths import (
    cache_value_updates_total_metric,
    device_status_metric,
    device_value_updates_metric,
    metric_root,
    session_busy_metric,
)

SCRIPTS_KEY = "exp/scripts"
CACHE_VALUE_KEY_SUFFIX = "/value"
CACHE_STATUS_KEY_SUFFIX = "/status"
_CACHE_METRIC_KEY_RULES = (
    ("exact", SCRIPTS_KEY, "session_busy"),
    ("suffix", CACHE_VALUE_KEY_SUFFIX, "device_value_updates"),
    ("suffix", CACHE_STATUS_KEY_SUFFIX, "device_status"),
)


def _build_cache_metric_key_filters() -> tuple[str, ...]:
    filters = []
    for match_type, pattern, _metric_family in _CACHE_METRIC_KEY_RULES:
        if match_type == "exact":
            filters.append(rf"^{re.escape(pattern)}$")
        elif match_type == "suffix":
            filters.append(rf".+{re.escape(pattern)}$")
        else:
            raise ValueError(f"Unsupported cache metric match type: {match_type!r}")
    return tuple(filters)


CACHE_METRIC_KEY_FILTERS = _build_cache_metric_key_filters()

_STATUS_CODE_TO_ORDINAL = {
    status.OK: 0,
    status.WARN: 1,
    status.BUSY: 2,
    status.NOTREACHED: 3,
    status.DISABLED: 4,
    status.ERROR: 5,
    status.UNKNOWN: 6,
}


def _parse_metric_timestamp(timestamp: str) -> int | None:
    try:
        return int(float(timestamp))
    except (TypeError, ValueError, OverflowError):
        return None


def _is_scripts_value_busy(value: object | None) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        compact = "".join(value.split())
        return compact not in {"", "[]"}
    return bool(value)


def classify_cache_metric_key(key: str) -> str | None:
    """Return the metric family handled for one collector cache key."""
    for match_type, pattern, metric_family in _CACHE_METRIC_KEY_RULES:
        if match_type == "exact" and key == pattern:
            return metric_family
        if match_type == "suffix" and key.endswith(pattern):
            return metric_family
    return None


def _device_name_from_cache_key(key: str) -> str:
    return key.partition("/")[0]


class CacheMetricsEmitter:
    """Emit Carbon metrics for the small set of cache keys this backend owns.

    Supported keys are classified in one place by :func:`classify_cache_metric_key`.
    The current backend emits:

    - ``<root>.session.busy`` from ``exp/scripts``
    - ``<root>.device.<name>.status`` from ``<device>/status``
    - flush-windowed ``/value`` update counters
    """

    def __init__(
        self,
        client,
        prefix: str,
        instrument: str,
        flush_interval_s: float,
        time_fn: Callable[[], float] = time.time,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ):
        self._client = client
        self._metric_root = metric_root(prefix, instrument)
        self.flush_interval_s = flush_interval_s
        self._time_fn = time_fn
        self._monotonic_fn = monotonic_fn
        self._value_update_counts = defaultdict(int)
        self._pending_condition = Condition()
        self._pending_since: float | None = None
        self._stop_flush_worker = False
        self._flush_thread: Thread | None = None
        if self.flush_interval_s > 0:
            self._flush_thread = Thread(
                target=self._flush_loop,
                name="ess-carbon-cache-flush",
                daemon=True,
            )
            self._flush_thread.start()

    def process_cache_update(
        self, timestamp: str, key: str, value: object | None
    ) -> list[str]:
        """Process one cache update and return any metric lines that were sent.

        ``timestamp`` must be parseable as a UNIX timestamp in seconds. Bad
        timestamps are treated as a dropped telemetry sample rather than a hard
        failure because collector telemetry must never destabilize NICOS.
        """
        metric_family = classify_cache_metric_key(key)
        if metric_family is None:
            return []

        emitted = []
        if metric_family == "session_busy":
            emitted.extend(self._emit_session_busy(timestamp, value))
        elif metric_family == "device_status":
            emitted.extend(self._emit_device_status(timestamp, key, value))
        elif value is not None:
            if self._record_value_update(key):
                emitted.extend(self.flush())
        return emitted

    def flush(self) -> list[str]:
        """Flush the current `/value` update window and return emitted lines."""
        with self._pending_condition:
            if not self._value_update_counts:
                self._pending_since = None
                return []
            snapshot = dict(self._value_update_counts)
            self._value_update_counts.clear()
            self._pending_since = None
            self._pending_condition.notify_all()

        timestamp = int(self._time_fn())
        total = sum(snapshot.values())
        lines = [
            (
                f"{cache_value_updates_total_metric(self._metric_root)} "
                f"{int(total)} {timestamp}\n"
            )
        ]
        for device_name, count in sorted(snapshot.items()):
            lines.append(
                f"{device_value_updates_metric(self._metric_root, device_name)} "
                f"{int(count)} {timestamp}\n"
            )
        self._client.send_lines(lines)
        return lines

    def _emit_session_busy(self, timestamp: str, value: object | None) -> list[str]:
        ts = _parse_metric_timestamp(timestamp)
        if ts is None:
            return []

        busy = int(_is_scripts_value_busy(value))
        lines = [f"{session_busy_metric(self._metric_root)} {busy} {ts}\n"]
        self._client.send_lines(lines)
        return lines

    def _emit_device_status(
        self, timestamp: str, key: str, value: object | None
    ) -> list[str]:
        ts = _parse_metric_timestamp(timestamp)
        if ts is None:
            return []
        if value is None:
            return []
        try:
            loaded = cache_load(str(value))
            code = int(loaded[0])
        except Exception:
            return []
        ordinal = _STATUS_CODE_TO_ORDINAL.get(code, 6)
        device_name = _device_name_from_cache_key(key)
        if not device_name:
            return []
        lines = [
            f"{device_status_metric(self._metric_root, device_name)} {ordinal} {ts}\n"
        ]
        self._client.send_lines(lines)
        return lines

    def _record_value_update(self, key: str) -> bool:
        device_name = _device_name_from_cache_key(key)
        if not device_name:
            return False
        with self._pending_condition:
            was_empty = not self._value_update_counts
            self._value_update_counts[device_name] += 1
            if self.flush_interval_s == 0:
                return True
            if was_empty:
                self._pending_since = self._monotonic_fn()
                self._pending_condition.notify_all()
        return False

    def _flush_loop(self) -> None:
        logger = logging.getLogger(__name__)
        while True:
            with self._pending_condition:
                while not self._stop_flush_worker and not self._value_update_counts:
                    self._pending_condition.wait()
                if self._stop_flush_worker:
                    return
                if self._pending_since is None:
                    self._pending_since = self._monotonic_fn()
                deadline = self._pending_since + self.flush_interval_s
                remaining = deadline - self._monotonic_fn()
                if remaining > 0:
                    self._pending_condition.wait(timeout=remaining)
                    continue
            try:
                self.flush()
            except Exception:
                logger.debug("Cache metric flush failed", exc_info=True)

    def close(self) -> None:
        if self._flush_thread is not None:
            with self._pending_condition:
                self._stop_flush_worker = True
                self._pending_condition.notify_all()
            self._flush_thread.join(timeout=1.0)
            self._flush_thread = None
        self.flush()
        self._client.close()
