# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

"""Translate NICOS cache updates into Carbon metric lines."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from nicos.protocols.cache import cache_load
from nicos_ess.telemetry.carbon.paths import sanitize_path, sanitize_segment

SCRIPTS_KEY = "exp/scripts"

_STATUS_CODE_TO_ORDINAL = {
    200: 0,  # ok
    210: 1,  # warn
    220: 2,  # busy
    230: 3,  # notreached
    235: 4,  # disabled
    240: 5,  # error
    999: 6,  # unknown
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


class CacheMetricsEmitter:
    """Turn selected NICOS cache updates into metric lines.

    The emitter is intentionally narrow for the first telemetry iteration: it
    only watches a small set of well-defined cache keys and ignores everything
    else. Callers may hand every collector update to
    :meth:`process_cache_update`; unsupported keys return no metric lines and
    cause no side effects. The emitter does not own retry logic or scheduling;
    those responsibilities stay in the caller and the configured sender.

    Two metric families are emitted:

    - immediate gauge updates derived from specific cache keys such as
      ``exp/scripts``
    - flush-windowed counters derived from noisy cache traffic, currently
      ``*/value`` updates
    """

    def __init__(
        self,
        client,
        prefix: str,
        instrument: str,
        flush_interval_s: float,
        time_fn=time.time,
        monotonic_fn=time.monotonic,
    ):
        self._client = client
        self._metric_root = f"{sanitize_path(prefix)}.{sanitize_segment(instrument)}"
        self.flush_interval_s = flush_interval_s
        self._time_fn = time_fn
        self._monotonic_fn = monotonic_fn
        self._last_flush_at = monotonic_fn()
        self._value_update_counts = defaultdict(int)
        self._counter_lock = Lock()

    def process_cache_update(
        self, timestamp: str, key: str, value: object | None
    ) -> list[str]:
        """Process one cache update and return any metric lines that were sent.

        ``timestamp`` must be parseable as a UNIX timestamp in seconds. Bad
        timestamps are treated as a dropped telemetry sample rather than a hard
        failure because collector telemetry must never destabilize NICOS.
        """
        emitted = []
        if key == SCRIPTS_KEY:
            emitted.extend(self._emit_session_busy(timestamp, value))
        elif key.endswith("/status"):
            emitted.extend(self._emit_device_status(timestamp, key, value))
        elif value is not None and key.endswith("/value"):
            self._record_value_update(key)

        if self._should_flush():
            emitted.extend(self.flush())
        return emitted

    def flush(self) -> list[str]:
        """Flush the current `/value` update window and return emitted lines."""
        with self._counter_lock:
            if not self._value_update_counts:
                self._last_flush_at = self._monotonic_fn()
                return []
            snapshot = dict(self._value_update_counts)
            self._value_update_counts.clear()
            self._last_flush_at = self._monotonic_fn()

        timestamp = int(self._time_fn())
        total = sum(snapshot.values())
        lines = [
            (
                f"{self._metric_root}.cache.value_updates.total.count "
                f"{int(total)} {timestamp}\n"
            )
        ]
        for device_name, count in sorted(snapshot.items()):
            device_segment = sanitize_segment(device_name)
            lines.append(
                (
                    f"{self._metric_root}.device.{device_segment}."
                    f"cache.value_updates.count {int(count)} {timestamp}\n"
                )
            )
        self._client.send_lines(lines)
        return lines

    def _emit_session_busy(self, timestamp: str, value: object | None) -> list[str]:
        ts = _parse_metric_timestamp(timestamp)
        if ts is None:
            return []

        busy = int(_is_scripts_value_busy(value))
        lines = [f"{self._metric_root}.session.busy {busy} {ts}\n"]
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
        device_name = key.partition("/")[0]
        if not device_name:
            return []
        device_segment = sanitize_segment(device_name)
        lines = [f"{self._metric_root}.device.{device_segment}.status {ordinal} {ts}\n"]
        self._client.send_lines(lines)
        return lines

    def _record_value_update(self, key: str) -> None:
        device_name, _slash, _param = key.partition("/")
        if not device_name:
            return
        with self._counter_lock:
            self._value_update_counts[device_name] += 1

    def _should_flush(self) -> bool:
        if self.flush_interval_s == 0:
            return True
        return self._monotonic_fn() - self._last_flush_at >= self.flush_interval_s

    def close(self):
        self.flush()
        self._client.close()
