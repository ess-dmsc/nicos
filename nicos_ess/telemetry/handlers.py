"""Facility-local log-to-metrics handlers."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from threading import Lock
from typing import Callable

from nicos import session
from nicos.core import ConfigurationError
from nicos.utils.loggers import ACTION, INPUT
from nicos_ess.telemetry.carbon import CarbonTcpClient, sanitize_path, sanitize_segment

_LOG_LEVEL_BUCKETS = {
    logging.DEBUG: "debug",
    logging.INFO: "info",
    ACTION: "action",
    INPUT: "input",
    logging.WARNING: "warning",
    logging.ERROR: "error",
    logging.CRITICAL: "critical",
}


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
    """Aggregate NICOS log-level counters and flush them to Carbon."""

    def __init__(
        self,
        instrument: str,
        prefix: str,
        client: CarbonTcpClient,
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


def create_log_handlers(config):
    """Create facility-local log handlers based on ESS config keys."""
    if not _parse_bool(getattr(config, "telemetry_enabled", False)):
        return []

    host = getattr(config, "telemetry_carbon_host", None)
    if not host:
        raise ConfigurationError(
            "telemetry_enabled=true requires telemetry_carbon_host"
        )

    port = _parse_int(getattr(config, "telemetry_carbon_port", 2003), 2003)
    prefix = str(getattr(config, "telemetry_prefix", "nicos"))
    instrument = str(getattr(config, "instrument", "unknown"))
    service_name = str(getattr(session, "appname", "unknown"))
    flush_interval_s = _parse_float(
        getattr(config, "telemetry_flush_interval_s", 10), 10
    )
    heartbeat_interval_s = _parse_float(
        getattr(config, "telemetry_heartbeat_interval_s", 10), 10
    )
    reconnect_delay_s = _parse_float(
        getattr(config, "telemetry_reconnect_delay_s", 2), 2
    )
    queue_max = _parse_int(getattr(config, "telemetry_queue_max", 10000), 10000)
    connect_timeout_s = _parse_float(
        getattr(config, "telemetry_connect_timeout_s", 1), 1
    )
    send_timeout_s = _parse_float(getattr(config, "telemetry_send_timeout_s", 1), 1)

    client = CarbonTcpClient(
        host=host,
        port=port,
        reconnect_delay_s=reconnect_delay_s,
        queue_max=queue_max,
        connect_timeout_s=connect_timeout_s,
        send_timeout_s=send_timeout_s,
    )
    return [
        LogLevelCounterHandler(
            instrument=instrument,
            prefix=prefix,
            client=client,
            service_name=service_name,
            flush_interval_s=flush_interval_s,
            heartbeat_interval_s=heartbeat_interval_s,
        )
    ]
