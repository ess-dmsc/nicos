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

"""Facility-local log-to-metrics handlers."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from threading import Lock
from typing import Callable

from nicos import session
from nicos.utils.loggers import ACTION, INPUT
from nicos_ess.telemetry.carbon import sanitize_path, sanitize_segment
from nicos_ess.telemetry.config import create_carbon_client, read_carbon_config
from nicos_ess.telemetry.sender import TelemetrySender

_LOG_LEVEL_BUCKETS = {
    logging.DEBUG: "debug",
    logging.INFO: "info",
    ACTION: "action",
    INPUT: "input",
    logging.WARNING: "warning",
    logging.ERROR: "error",
    logging.CRITICAL: "critical",
}


def _normalize_level(levelno: int, levelname: str) -> str:
    if levelno in _LOG_LEVEL_BUCKETS:
        return _LOG_LEVEL_BUCKETS[levelno]

    normalized_name = sanitize_segment(levelname)
    if normalized_name in _LOG_LEVEL_BUCKETS.values():
        return normalized_name

    if levelno >= logging.CRITICAL:
        return "critical"
    if levelno >= logging.ERROR:
        return "error"
    if levelno >= logging.WARNING:
        return "warning"
    if levelno >= logging.INFO:
        return "info"
    if levelno >= logging.DEBUG:
        return "debug"
    return "other"


class LogLevelCounterHandler(logging.Handler):
    """Aggregate NICOS log records into counter metrics.

    The handler accepts ordinary NICOS log records, groups them by normalized
    level name, and periodically emits Graphite-style counter samples through
    the provided sender. The sender is expected to be non-throwing during normal
    outages: network failures should be handled inside the sender so logging
    itself stays stable. The handler owns an optional heartbeat thread, so
    callers must call :meth:`close` during shutdown to flush counters and stop
    that background work cleanly.
    """

    def __init__(
        self,
        instrument: str,
        prefix: str,
        client: TelemetrySender,
        flush_interval_s: float = 10.0,
        service_name: str | None = None,
        heartbeat_interval_s: float = 10.0,
        start_heartbeat_thread: bool = True,
        time_fn: Callable[[], float] = time.time,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ):
        super().__init__(level=logging.DEBUG)
        self.client = client
        self.flush_interval_s = max(float(flush_interval_s), 0.0)
        self.heartbeat_interval_s = max(float(heartbeat_interval_s), 0.0)
        self._time_fn = time_fn
        self._monotonic_fn = monotonic_fn
        self._metric_root = f"{sanitize_path(prefix)}.{sanitize_segment(instrument)}"
        service_segment = sanitize_segment(service_name or "unknown")
        self._service_root = f"{self._metric_root}.service.{service_segment}"
        self._last_flush_at = monotonic_fn()
        self._counters = defaultdict(int)
        self._counter_lock = Lock()
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread = None
        if self.heartbeat_interval_s > 0 and start_heartbeat_thread:
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                name="ess-telemetry-heartbeat",
                daemon=True,
            )
            self._heartbeat_thread.start()

    def emit(self, record):
        try:
            now = self._monotonic_fn()
            bucket = _normalize_level(record.levelno, record.levelname)
            with self._counter_lock:
                self._counters["logs.total.count"] += 1
                self._counters[f"logs.level.{bucket}.count"] += 1
                should_flush = now - self._last_flush_at >= self.flush_interval_s
            if should_flush:
                self.flush()
        except Exception:
            self.handleError(record)

    def flush(self):
        with self._counter_lock:
            if not self._counters:
                return
            snapshot = dict(self._counters)
            self._counters.clear()
            self._last_flush_at = self._monotonic_fn()

        timestamp = int(self._time_fn())
        lines = []
        for suffix, value in sorted(snapshot.items()):
            lines.append(f"{self._service_root}.{suffix} {int(value)} {timestamp}\n")

        self.client.send_lines(lines)

    def emit_heartbeat(self):
        """Emit a heartbeat sample for liveness dashboards."""
        timestamp = int(self._time_fn())
        self.client.send_lines(
            [f"{self._service_root}.telemetry.heartbeat 1 {timestamp}\n"]
        )

    def _heartbeat_loop(self):
        while not self._heartbeat_stop.wait(self.heartbeat_interval_s):
            try:
                self.emit_heartbeat()
            except Exception:
                # Never let telemetry background work destabilize NICOS logging.
                pass

    def close(self):
        try:
            self._heartbeat_stop.set()
            if self._heartbeat_thread:
                self._heartbeat_thread.join(timeout=1.0)
            self.flush()
            self.client.flush()
        finally:
            self.client.close()
            super().close()


def create_log_handlers(nicos_config):
    """Create facility-local log handlers based on ESS config keys."""
    cfg = read_carbon_config(nicos_config)
    if cfg is None:
        return []

    service_name = str(getattr(session, "appname", "unknown"))
    client = create_carbon_client(cfg)

    return [
        LogLevelCounterHandler(
            instrument=cfg.instrument,
            prefix=cfg.prefix,
            client=client,
            service_name=service_name,
            flush_interval_s=cfg.flush_interval_s,
            heartbeat_interval_s=cfg.heartbeat_interval_s,
        )
    ]
