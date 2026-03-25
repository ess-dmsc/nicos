"""Helpers for Graphite-safe Carbon metric names."""

from __future__ import annotations

import re

_VALID_SEGMENT_RE = re.compile(r"[^A-Za-z0-9_-]+")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


def sanitize_segment(segment: str) -> str:
    """Convert one metric path segment to a Graphite-safe token."""
    text = _VALID_SEGMENT_RE.sub("_", str(segment).strip().lower())
    text = _MULTI_UNDERSCORE_RE.sub("_", text).strip("_")
    return text or "unknown"


def sanitize_path(path: str) -> str:
    """Sanitize a dot-delimited metric path."""
    parts = [sanitize_segment(part) for part in str(path).split(".") if part]
    return ".".join(parts) if parts else "unknown"


def metric_root(prefix: str, instrument: str) -> str:
    """Build the shared metric root for one NICOS instrument."""
    return f"{sanitize_path(prefix)}.{sanitize_segment(instrument)}"


def device_metric_root(root: str, device_name: str) -> str:
    """Build the metric root for one device below an instrument root."""
    return f"{root}.device.{sanitize_segment(device_name)}"


def service_metric_root(root: str, service_name: str) -> str:
    """Build the metric root for one NICOS service below an instrument root."""
    return f"{root}.service.{sanitize_segment(service_name)}"


def session_busy_metric(root: str) -> str:
    """Metric name for experiment-script busy state."""
    return f"{root}.session.busy"


def cache_value_updates_total_metric(root: str) -> str:
    """Metric name for total `/value` updates in one flush window."""
    return f"{root}.cache.value_updates.total.count"


def device_value_updates_metric(root: str, device_name: str) -> str:
    """Metric name for one device's `/value` update count."""
    return f"{device_metric_root(root, device_name)}.cache.value_updates.count"


def device_status_metric(root: str, device_name: str) -> str:
    """Metric name for one device's status ordinal."""
    return f"{device_metric_root(root, device_name)}.status"


def service_logs_total_metric(service_root: str) -> str:
    """Metric name for total log records in one flush window."""
    return f"{service_root}.logs.total.count"


def service_log_level_metric(service_root: str, bucket: str) -> str:
    """Metric name for one normalized log-level counter."""
    return f"{service_root}.logs.level.{sanitize_segment(bucket)}.count"


def service_heartbeat_metric(service_root: str) -> str:
    """Metric name for telemetry heartbeat samples."""
    return f"{service_root}.telemetry.heartbeat"
