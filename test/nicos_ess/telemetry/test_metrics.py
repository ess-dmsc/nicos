"""Tests for nicos_ess.telemetry.metrics (CacheMetricsEmitter)."""

import pytest

from nicos_ess.telemetry.metrics import SCRIPTS_KEY, CacheMetricsEmitter


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


def _all_metrics(client):
    """Flatten all sent batches into a single parsed dict."""
    all_lines = [line for batch in client.sent_batches for line in batch]
    return _parse_metrics(all_lines)


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

        metrics = _all_metrics(client)
        # Last value for the metric key wins in our flat parse, but we
        # verify all three sends happened.
        assert len(client.sent_batches) == 3
