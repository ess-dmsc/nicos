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

"""Cache-derived metrics for Carbon/Graphite."""

from __future__ import annotations

from nicos_ess.telemetry.carbon import sanitize_path, sanitize_segment
from nicos_ess.telemetry.sender import TelemetrySender

SCRIPTS_KEY = "exp/scripts"


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
    """

    def __init__(
        self,
        client: TelemetrySender,
        prefix: str,
        instrument: str,
    ):
        self._client = client
        self._metric_root = f"{sanitize_path(prefix)}.{sanitize_segment(instrument)}"

    def process_cache_update(
        self, timestamp: str, key: str, value: object | None
    ) -> list[str]:
        """Process one cache update and return any metric lines that were sent.

        ``timestamp`` must be parseable as a UNIX timestamp in seconds. Bad
        timestamps are treated as a dropped telemetry sample rather than a hard
        failure because collector telemetry must never destabilize NICOS.
        """
        if key == SCRIPTS_KEY:
            return self._emit_session_busy(timestamp, value)
        return []

    def _emit_session_busy(self, timestamp: str, value: object | None) -> list[str]:
        ts = _parse_metric_timestamp(timestamp)
        if ts is None:
            return []

        busy = int(_is_scripts_value_busy(value))
        lines = [f"{self._metric_root}.session.busy {busy} {ts}\n"]
        self._client.send_lines(lines)
        return lines

    def close(self):
        self._client.close()
