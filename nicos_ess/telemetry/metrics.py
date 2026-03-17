"""Cache-derived metrics for Carbon/Graphite."""

from __future__ import annotations

import time
from typing import Callable

from nicos_ess.telemetry.carbon import CarbonTcpClient, sanitize_path, sanitize_segment

SCRIPTS_KEY = "exp/scripts"


class CacheMetricsEmitter:
    """Transforms NICOS cache key updates into Carbon/Graphite metrics."""

    def __init__(
        self,
        client: CarbonTcpClient,
        prefix: str,
        instrument: str,
        time_fn: Callable[[], float] = time.time,
    ):
        self._client = client
        self._metric_root = f"{sanitize_path(prefix)}.{sanitize_segment(instrument)}"
        self._time_fn = time_fn

    def process_cache_update(
        self, timestamp: str, key: str, value: str | None
    ) -> list[str]:
        """Process a cache key change. Returns the metric lines produced."""
        if key == SCRIPTS_KEY:
            return self._emit_session_busy(timestamp, value)
        return []

    def _emit_session_busy(self, timestamp: str, value: str | None) -> list[str]:
        busy = 0 if value is None or value == "[]" else 1
        ts = int(float(timestamp))
        lines = [f"{self._metric_root}.session.busy {busy} {ts}\n"]
        self._client.send_lines(lines)
        return lines

    def close(self):
        self._client.close()
