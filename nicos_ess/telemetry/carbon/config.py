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

"""Parse Carbon settings for the ESS telemetry backend."""

from __future__ import annotations

from dataclasses import dataclass

from nicos_ess.telemetry.carbon.client import CarbonTcpClient


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
    """Resolved Carbon settings read from ``nicos.conf``."""

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

    @classmethod
    def from_nicos_config(cls, nicos_config) -> CarbonConfig | None:
        """Read Carbon config from a NICOS config object."""
        if not _parse_bool(getattr(nicos_config, "telemetry_enabled", False)):
            return None

        host = getattr(nicos_config, "telemetry_carbon_host", None)
        host = "" if host is None else str(host).strip()
        if not host:
            from nicos.core import ConfigurationError

            raise ConfigurationError(
                "telemetry_enabled=true requires telemetry_carbon_host"
            )

        return cls(
            host=host,
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
