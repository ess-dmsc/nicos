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

"""Tests for nicos_ess.telemetry.metrics (CacheMetricsEmitter)."""

import pytest

from nicos_ess.telemetry.metrics import SCRIPTS_KEY, CacheMetricsEmitter


class CapturingClient:
    """Minimal CarbonTcpClient stand-in that captures sent lines."""

    def __init__(self):
        self.sent_batches = []
        self.closed = False
        self.flush_calls = 0

    def send_lines(self, lines):
        self.sent_batches.append(list(lines))
        return True

    def flush(self):
        self.flush_calls += 1
        return True

    def close(self):
        self.closed = True


def _parse_metrics(lines):
    parsed = {}
    for line in lines:
        metric, value, timestamp = line.strip().split(" ")
        parsed[metric] = (int(value), int(timestamp))
    return parsed


class TestCacheMetricsEmitter:
    @pytest.fixture()
    def client(self):
        return CapturingClient()

    @pytest.fixture()
    def emitter(self, client):
        return CacheMetricsEmitter(
            client=client,
            prefix="nicos",
            instrument="BIFROST",
        )

    def test_scripts_empty_emits_idle(self, client, emitter):
        lines = emitter.process_cache_update("1710000000", SCRIPTS_KEY, "[]")
        assert len(lines) == 1
        metrics = _parse_metrics(lines)
        assert metrics["nicos.bifrost.session.busy"] == (0, 1710000000)

    def test_scripts_nonempty_emits_busy(self, client, emitter):
        lines = emitter.process_cache_update(
            "1710000000", SCRIPTS_KEY, "['move(mx, 1)']"
        )
        metrics = _parse_metrics(lines)
        assert metrics["nicos.bifrost.session.busy"] == (1, 1710000000)

    def test_scripts_none_value_treated_as_idle(self, client, emitter):
        lines = emitter.process_cache_update("1710000000", SCRIPTS_KEY, None)
        metrics = _parse_metrics(lines)
        assert metrics["nicos.bifrost.session.busy"] == (0, 1710000000)

    def test_scripts_whitespace_only_list_is_treated_as_idle(self, client, emitter):
        lines = emitter.process_cache_update("1710000000", SCRIPTS_KEY, "[   ]")
        metrics = _parse_metrics(lines)
        assert metrics["nicos.bifrost.session.busy"] == (0, 1710000000)

    def test_unrelated_key_produces_no_metrics(self, client, emitter):
        lines = emitter.process_cache_update(
            "1710000000", "motor1/value", "42.0"
        )
        assert lines == []
        assert client.sent_batches == []

    def test_metrics_sent_to_client(self, client, emitter):
        emitter.process_cache_update("1710000000", SCRIPTS_KEY, "[]")
        assert len(client.sent_batches) == 1
        metrics = _parse_metrics(client.sent_batches[0])
        assert "nicos.bifrost.session.busy" in metrics

    def test_timestamp_is_truncated_to_int(self, client, emitter):
        lines = emitter.process_cache_update(
            "1710000000.123", SCRIPTS_KEY, "[]"
        )
        metrics = _parse_metrics(lines)
        assert metrics["nicos.bifrost.session.busy"] == (0, 1710000000)

    def test_bad_timestamp_drops_sample(self, client, emitter):
        lines = emitter.process_cache_update("not-a-timestamp", SCRIPTS_KEY, "[]")
        assert lines == []
        assert client.sent_batches == []

    def test_custom_prefix_and_instrument(self, client):
        emitter = CacheMetricsEmitter(
            client=client, prefix="ess.prod", instrument="YMIR"
        )
        lines = emitter.process_cache_update("1710000000", SCRIPTS_KEY, "[]")
        metrics = _parse_metrics(lines)
        assert "ess.prod.ymir.session.busy" in metrics

    def test_close_closes_client(self, client, emitter):
        emitter.close()
        assert client.closed

    def test_transition_idle_to_busy_to_idle(self, client, emitter):
        emitter.process_cache_update("100", SCRIPTS_KEY, "[]")
        emitter.process_cache_update("200", SCRIPTS_KEY, "['scan()']")
        emitter.process_cache_update("300", SCRIPTS_KEY, "[]")

        busy_values = [
            _parse_metrics(batch)["nicos.bifrost.session.busy"][0]
            for batch in client.sent_batches
        ]
        assert busy_values == [0, 1, 0]
