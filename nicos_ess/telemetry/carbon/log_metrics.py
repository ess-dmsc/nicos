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

"""Translate NICOS log records into Carbon counter metrics."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable

from nicos import session
from nicos.utils.loggers import ACTION, INPUT
from nicos_ess.telemetry.carbon.config import CarbonConfig
from nicos_ess.telemetry.carbon.paths import (
    metric_root,
    sanitize_segment,
    service_heartbeat_metric,
    service_log_level_metric,
    service_logs_total_metric,
    service_metric_root,
)

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


class CarbonLogLevelCounterHandler(logging.Handler):
    """Count NICOS log records and emit them below one service metric root."""

    def __init__(
        self,
        instrument: str,
        prefix: str,
        client,
        flush_interval_s: float = 10.0,
        service_name: str | None = None,
        heartbeat_interval_s: float = 10.0,
        start_heartbeat_thread: bool = True,
        time_fn: Callable[[], float] = time.time,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ):
        super().__init__(level=logging.DEBUG)
        self.client = client
        self.flush_interval_s = flush_interval_s
        self.heartbeat_interval_s = heartbeat_interval_s
        self._time_fn = time_fn
        self._monotonic_fn = monotonic_fn
        self._metric_root = metric_root(prefix, instrument)
        self._service_root = service_metric_root(
            self._metric_root, service_name or "unknown"
        )
        self._level_counts = defaultdict(int)
        self._total_count = 0
        self._pending_condition = threading.Condition()
        self._pending_since: float | None = None
        self._stop_flush_worker = False
        self._flush_thread = None
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread = None
        if self.flush_interval_s > 0:
            self._flush_thread = threading.Thread(
                target=self._flush_loop,
                name="ess-telemetry-log-flush",
                daemon=True,
            )
            self._flush_thread.start()
        if self.heartbeat_interval_s > 0 and start_heartbeat_thread:
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                name="ess-telemetry-heartbeat",
                daemon=True,
            )
            self._heartbeat_thread.start()

    def emit(self, record):
        try:
            bucket = _normalize_level(record.levelno, record.levelname)
            should_flush = False
            with self._pending_condition:
                was_empty = self._total_count == 0 and not self._level_counts
                self._total_count += 1
                self._level_counts[bucket] += 1
                if self.flush_interval_s == 0:
                    should_flush = True
                elif was_empty:
                    self._pending_since = self._monotonic_fn()
                    self._pending_condition.notify_all()
            if should_flush:
                self.flush()
        except Exception:
            self.handleError(record)

    def flush(self):
        with self._pending_condition:
            if self._total_count == 0 and not self._level_counts:
                self._pending_since = None
                return
            total_count = self._total_count
            level_snapshot = dict(self._level_counts)
            self._total_count = 0
            self._level_counts.clear()
            self._pending_since = None
            self._pending_condition.notify_all()

        timestamp = int(self._time_fn())
        lines = [
            f"{service_logs_total_metric(self._service_root)} "
            f"{total_count} {timestamp}\n"
        ]
        for bucket, value in sorted(level_snapshot.items()):
            lines.append(
                f"{service_log_level_metric(self._service_root, bucket)} "
                f"{int(value)} {timestamp}\n"
            )

        self.client.send_lines(lines)

    def emit_heartbeat(self):
        """Emit a heartbeat sample for liveness dashboards."""
        timestamp = int(self._time_fn())
        self.client.send_lines(
            [f"{service_heartbeat_metric(self._service_root)} 1 {timestamp}\n"]
        )

    def _heartbeat_loop(self):
        while not self._heartbeat_stop.wait(self.heartbeat_interval_s):
            try:
                self.emit_heartbeat()
            except Exception:
                logging.getLogger(__name__).debug(
                    "Heartbeat emission failed", exc_info=True
                )

    def _flush_loop(self) -> None:
        logger = logging.getLogger(__name__)
        while True:
            with self._pending_condition:
                while (
                    not self._stop_flush_worker
                    and self._total_count == 0
                    and not self._level_counts
                ):
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
                logger.debug("Log metric flush failed", exc_info=True)

    def close(self):
        try:
            self._heartbeat_stop.set()
            if self._heartbeat_thread:
                self._heartbeat_thread.join(timeout=1.0)
            if self._flush_thread is not None:
                with self._pending_condition:
                    self._stop_flush_worker = True
                    self._pending_condition.notify_all()
                self._flush_thread.join(timeout=1.0)
                self._flush_thread = None
            self.flush()
            self.client.flush()
        finally:
            self.client.close()
            super().close()


def create_carbon_log_handlers(nicos_config):
    """Create facility-local log handlers based on ESS config keys."""
    cfg = CarbonConfig.from_nicos_config(nicos_config)
    if cfg is None:
        return []

    service_name = str(getattr(session, "appname", "unknown"))
    return build_carbon_log_handlers(cfg, service_name=service_name)


def build_carbon_log_handlers(cfg: CarbonConfig, service_name: str):
    """Build Carbon log metric handlers for one resolved config."""
    return [cfg.create_log_handler(service_name=service_name)]
