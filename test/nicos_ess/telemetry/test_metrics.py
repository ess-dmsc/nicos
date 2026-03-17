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

from nicos.protocols.cache import cache_dump
from nicos_ess.telemetry.metrics import SCRIPTS_KEY, CacheMetricsEmitter


class FakeClock:
    def __init__(self, value=0.0):
        self.value = float(value)

    def __call__(self):
        return self.value

    def advance(self, delta):
        self.value += float(delta)


class CapturingClient:
    """Minimal CarbonTcpClient stand-in that captures sent lines."""

    def __init__(self):
        self.sent_batches = []
        self.closed = False

    def send_lines(self, lines):
        self.sent_batches.append(list(lines))
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
            flush_interval_s=10.0,
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
            "1710000000", "motor1/target", "42.0"
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
            client=client,
            prefix="ess.prod",
            instrument="YMIR",
            flush_interval_s=10.0,
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

    def test_value_updates_are_counted_per_device_on_flush(self, client):
        monotonic_clock = FakeClock(100)
        emitter = CacheMetricsEmitter(
            client=client,
            prefix="nicos",
            instrument="BIFROST",
            flush_interval_s=10.0,
            time_fn=lambda: 1710000010,
            monotonic_fn=monotonic_clock,
        )

        emitter.process_cache_update("100", "motor1/value", "1")
        emitter.process_cache_update("101", "motor1/value", "2")
        emitter.process_cache_update("102", "detector/value", "3")

        lines = emitter.flush()
        metrics = _parse_metrics(lines)
        assert metrics["nicos.bifrost.cache.value_updates.total.count"] == (
            3,
            1710000010,
        )
        assert metrics["nicos.bifrost.device.motor1.cache.value_updates.count"] == (
            2,
            1710000010,
        )
        assert metrics["nicos.bifrost.device.detector.cache.value_updates.count"] == (
            1,
            1710000010,
        )

    def test_value_updates_flush_automatically_after_interval(self, client):
        monotonic_clock = FakeClock(10)
        emitter = CacheMetricsEmitter(
            client=client,
            prefix="nicos",
            instrument="BIFROST",
            flush_interval_s=5.0,
            time_fn=lambda: 1710000020,
            monotonic_fn=monotonic_clock,
        )

        emitter.process_cache_update("100", "motor1/value", "1")
        monotonic_clock.advance(5)
        lines = emitter.process_cache_update("101", "motor2/value", "2")

        metrics = _parse_metrics(lines)
        assert metrics["nicos.bifrost.cache.value_updates.total.count"] == (
            2,
            1710000020,
        )
        assert metrics["nicos.bifrost.device.motor1.cache.value_updates.count"] == (
            1,
            1710000020,
        )
        assert metrics["nicos.bifrost.device.motor2.cache.value_updates.count"] == (
            1,
            1710000020,
        )

    def test_value_updates_with_none_do_not_count(self, client, emitter):
        lines = emitter.process_cache_update("100", "motor1/value", None)
        assert lines == []
        assert emitter.flush() == []

    def test_status_update_emits_correct_ordinal(self, client, emitter):
        status_value = cache_dump((200, "idle"))
        lines = emitter.process_cache_update("1710000000", "motor1/status", status_value)
        assert len(lines) == 1
        metrics = _parse_metrics(lines)
        assert metrics["nicos.bifrost.device.motor1.status"] == (0, 1710000000)

    def test_status_unknown_code_maps_to_6(self, client, emitter):
        status_value = cache_dump((777, "custom"))
        lines = emitter.process_cache_update("1710000000", "motor1/status", status_value)
        metrics = _parse_metrics(lines)
        assert metrics["nicos.bifrost.device.motor1.status"] == (6, 1710000000)

    def test_status_transitions(self, client, emitter):
        for code, expected_ordinal in [(200, 0), (220, 2), (240, 5), (200, 0)]:
            status_value = cache_dump((code, "text"))
            emitter.process_cache_update(
                "1710000000", "motor1/status", status_value
            )

        status_values = [
            _parse_metrics(batch)["nicos.bifrost.device.motor1.status"][0]
            for batch in client.sent_batches
        ]
        assert status_values == [0, 2, 5, 0]

    def test_status_bad_value_is_dropped(self, client, emitter):
        lines = emitter.process_cache_update(
            "1710000000", "motor1/status", "not-a-tuple"
        )
        assert lines == []
        assert client.sent_batches == []

    def test_status_none_value_is_dropped(self, client, emitter):
        lines = emitter.process_cache_update("1710000000", "motor1/status", None)
        assert lines == []
        assert client.sent_batches == []

    def test_close_flushes_pending_value_update_counts(self, client):
        emitter = CacheMetricsEmitter(
            client=client,
            prefix="nicos",
            instrument="BIFROST",
            flush_interval_s=10.0,
            time_fn=lambda: 1710000030,
        )

        emitter.process_cache_update("100", "motor1/value", "1")
        emitter.close()

        assert client.closed is True
        assert len(client.sent_batches) == 1
        metrics = _parse_metrics(client.sent_batches[0])
        assert metrics["nicos.bifrost.cache.value_updates.total.count"] == (
            1,
            1710000030,
        )
