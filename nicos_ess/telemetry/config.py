"""Shared Carbon/Graphite telemetry configuration."""

from __future__ import annotations

from dataclasses import dataclass

from nicos_ess.telemetry.carbon import CarbonTcpClient


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


@dataclass(frozen=True)
class CarbonConfig:
    """All Carbon/Graphite telemetry settings from nicos.conf."""

    host: str
    port: int = 2003
    prefix: str = "nicos"
    instrument: str = "unknown"
    flush_interval_s: float = 10.0
    heartbeat_interval_s: float = 10.0
    reconnect_delay_s: float = 2.0
    queue_max: int = 10000
    connect_timeout_s: float = 1.0
    send_timeout_s: float = 1.0


def read_carbon_config(nicos_config) -> CarbonConfig | None:
    """Read Carbon config from a NICOS config object.

    Returns None if telemetry is disabled. Raises ConfigurationError
    if telemetry is enabled but the host is missing.
    """
    if not _parse_bool(getattr(nicos_config, "telemetry_enabled", False)):
        return None

    host = getattr(nicos_config, "telemetry_carbon_host", None)
    if not host:
        from nicos.core import ConfigurationError

        raise ConfigurationError(
            "telemetry_enabled=true requires telemetry_carbon_host"
        )

    return CarbonConfig(
        host=str(host),
        port=_parse_int(getattr(nicos_config, "telemetry_carbon_port", 2003), 2003),
        prefix=str(getattr(nicos_config, "telemetry_prefix", "nicos")),
        instrument=str(getattr(nicos_config, "instrument", "unknown")),
        flush_interval_s=_parse_float(
            getattr(nicos_config, "telemetry_flush_interval_s", 10), 10
        ),
        heartbeat_interval_s=_parse_float(
            getattr(nicos_config, "telemetry_heartbeat_interval_s", 10), 10
        ),
        reconnect_delay_s=_parse_float(
            getattr(nicos_config, "telemetry_reconnect_delay_s", 2), 2
        ),
        queue_max=_parse_int(
            getattr(nicos_config, "telemetry_queue_max", 10000), 10000
        ),
        connect_timeout_s=_parse_float(
            getattr(nicos_config, "telemetry_connect_timeout_s", 1), 1
        ),
        send_timeout_s=_parse_float(
            getattr(nicos_config, "telemetry_send_timeout_s", 1), 1
        ),
    )


def create_carbon_client(cfg: CarbonConfig) -> CarbonTcpClient:
    """Create a CarbonTcpClient from a CarbonConfig."""
    return CarbonTcpClient(
        host=cfg.host,
        port=cfg.port,
        reconnect_delay_s=cfg.reconnect_delay_s,
        queue_max=cfg.queue_max,
        connect_timeout_s=cfg.connect_timeout_s,
        send_timeout_s=cfg.send_timeout_s,
    )
