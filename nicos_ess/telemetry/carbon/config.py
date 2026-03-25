"""Parse Carbon settings for the ESS telemetry backend."""

from __future__ import annotations

from dataclasses import dataclass

from nicos.core import ConfigurationError
from nicos_ess.telemetry.carbon.client import CarbonTcpClient


def _parse_bool(setting_name, value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigurationError(
        f"{setting_name} must be one of true/false/1/0/yes/no/on/off, got {value!r}"
    )


def _parse_int(setting_name, value, default, *, minimum=None, maximum=None):
    if isinstance(value, bool):
        raise ConfigurationError(f"{setting_name} must be an integer, got {value!r}")
    try:
        parsed = default if value is None else int(value)
    except (TypeError, ValueError) as err:
        raise ConfigurationError(
            f"{setting_name} must be an integer, got {value!r}"
        ) from err
    if minimum is not None and parsed < minimum:
        raise ConfigurationError(f"{setting_name} must be >= {minimum}, got {parsed}")
    if maximum is not None and parsed > maximum:
        raise ConfigurationError(f"{setting_name} must be <= {maximum}, got {parsed}")
    return parsed


def _parse_float(setting_name, value, default, *, minimum=None):
    if isinstance(value, bool):
        raise ConfigurationError(f"{setting_name} must be a number, got {value!r}")
    try:
        parsed = default if value is None else float(value)
    except (TypeError, ValueError) as err:
        raise ConfigurationError(
            f"{setting_name} must be a number, got {value!r}"
        ) from err
    if minimum is not None and parsed < minimum:
        raise ConfigurationError(f"{setting_name} must be >= {minimum}, got {parsed}")
    return parsed


def _parse_text(setting_name, value, default):
    if value is None:
        text = default
    elif isinstance(value, str):
        text = value
    else:
        raise ConfigurationError(
            f"{setting_name} must be a non-blank string, got {value!r}"
        )
    text = text.strip()
    if not text:
        raise ConfigurationError(f"{setting_name} must not be blank")
    return text


@dataclass(frozen=True)
class CarbonConfig:
    """Resolved Carbon settings read from ``nicos.conf``."""

    host: str
    port: int = 2003
    prefix: str = "nicosserver"
    instrument: str = "unknown"
    flush_interval_s: float = 10.0
    heartbeat_interval_s: float = 10.0
    reconnect_delay_s: float = 2.0
    queue_max: int = 10000
    connect_timeout_s: float = 1.0
    send_timeout_s: float = 1.0

    @classmethod
    def from_nicos_config(cls, nicos_config) -> CarbonConfig | None:
        """Read Carbon config from a NICOS config object."""
        if not _parse_bool(
            "telemetry_enabled", getattr(nicos_config, "telemetry_enabled", False)
        ):
            return None

        return cls(
            host=_parse_text(
                "telemetry_carbon_host",
                getattr(nicos_config, "telemetry_carbon_host", None),
                default="",
            ),
            port=_parse_int(
                "telemetry_carbon_port",
                getattr(nicos_config, "telemetry_carbon_port", 2003),
                2003,
                minimum=1,
                maximum=65535,
            ),
            prefix=_parse_text(
                "telemetry_prefix",
                getattr(nicos_config, "telemetry_prefix", "nicosserver"),
                default="nicosserver",
            ),
            instrument=_parse_text(
                "instrument",
                getattr(nicos_config, "instrument", "unknown"),
                default="unknown",
            ),
            flush_interval_s=_parse_float(
                "telemetry_flush_interval_s",
                getattr(nicos_config, "telemetry_flush_interval_s", 10),
                10,
                minimum=0,
            ),
            heartbeat_interval_s=_parse_float(
                "telemetry_heartbeat_interval_s",
                getattr(nicos_config, "telemetry_heartbeat_interval_s", 10),
                10,
                minimum=0,
            ),
            reconnect_delay_s=_parse_float(
                "telemetry_reconnect_delay_s",
                getattr(nicos_config, "telemetry_reconnect_delay_s", 2),
                2,
                minimum=0,
            ),
            queue_max=_parse_int(
                "telemetry_queue_max",
                getattr(nicos_config, "telemetry_queue_max", 10000),
                10000,
                minimum=1,
            ),
            connect_timeout_s=_parse_float(
                "telemetry_connect_timeout_s",
                getattr(nicos_config, "telemetry_connect_timeout_s", 1),
                1,
                minimum=0,
            ),
            send_timeout_s=_parse_float(
                "telemetry_send_timeout_s",
                getattr(nicos_config, "telemetry_send_timeout_s", 1),
                1,
                minimum=0,
            ),
        )

    def create_client(self) -> CarbonTcpClient:
        """Build the Carbon TCP client described by this config."""
        return CarbonTcpClient(
            host=self.host,
            port=self.port,
            reconnect_delay_s=self.reconnect_delay_s,
            queue_max=self.queue_max,
            connect_timeout_s=self.connect_timeout_s,
            send_timeout_s=self.send_timeout_s,
        )

    def create_cache_metrics_emitter(self):
        """Build the cache-update emitter described by this config."""
        from nicos_ess.telemetry.carbon.cache_metrics import CacheMetricsEmitter

        return CacheMetricsEmitter(
            client=self.create_client(),
            prefix=self.prefix,
            instrument=self.instrument,
            flush_interval_s=self.flush_interval_s,
        )

    def create_log_handler(self, service_name: str):
        """Build the log-metrics handler described by this config."""
        from nicos_ess.telemetry.carbon.log_metrics import CarbonLogLevelCounterHandler

        return CarbonLogLevelCounterHandler(
            instrument=self.instrument,
            prefix=self.prefix,
            client=self.create_client(),
            flush_interval_s=self.flush_interval_s,
            service_name=service_name,
            heartbeat_interval_s=self.heartbeat_interval_s,
        )
