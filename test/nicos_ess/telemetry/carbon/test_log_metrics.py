"""Tests for Carbon-backed log metric handlers."""

import logging
import time
from types import SimpleNamespace

import pytest

import nicos_ess
from nicos.core import ConfigurationError
from nicos.utils.loggers import ACTION, INPUT
from nicos_ess.telemetry.carbon.config import CarbonConfig
from nicos_ess.telemetry.carbon.log_metrics import (
    CarbonLogLevelCounterHandler,
    build_carbon_log_handlers,
    create_carbon_log_handlers,
)

FIXED_TIMESTAMP = 1773070701


class FakeClock:
    def __init__(self, value=0.0):
        self.value = float(value)

    def __call__(self):
        return self.value

    def advance(self, delta):
        self.value += float(delta)


class CapturingClient:
    def __init__(self):
        self.sent_batches = []
        self.flush_calls = 0
        self.closed = False

    def send_lines(self, lines):
        self.sent_batches.append(list(lines))
        return True

    def flush(self):
        self.flush_calls += 1
        return True

    def close(self):
        self.closed = True


def _make_record(levelno):
    return logging.LogRecord(
        name="nicos.test",
        level=levelno,
        pathname=__file__,
        lineno=1,
        msg="metric test",
        args=(),
        exc_info=None,
    )


def _parse_metrics(lines):
    parsed = {}
    for line in lines:
        metric, value, timestamp = line.strip().split(" ")
        parsed[metric] = (int(value), int(timestamp))
    return parsed


def _wait_until(predicate, timeout=1.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def test_carbon_log_level_counter_handler_emits_expected_metrics():
    clock = FakeClock(100)
    client = CapturingClient()
    handler = CarbonLogLevelCounterHandler(
        instrument="BIFROST",
        prefix="nicosserver",
        client=client,
        flush_interval_s=999,
        heartbeat_interval_s=0,
        start_heartbeat_thread=False,
        time_fn=lambda: FIXED_TIMESTAMP,
        monotonic_fn=clock,
    )

    for levelno in (
        logging.DEBUG,
        logging.INFO,
        ACTION,
        INPUT,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ):
        handler.emit(_make_record(levelno))

    handler.flush()
    assert len(client.sent_batches) == 1

    metrics = _parse_metrics(client.sent_batches[0])
    expected_counts = {
        "nicosserver.bifrost.service.unknown.logs.total.count": 7,
        "nicosserver.bifrost.service.unknown.logs.level.debug.count": 1,
        "nicosserver.bifrost.service.unknown.logs.level.info.count": 1,
        "nicosserver.bifrost.service.unknown.logs.level.action.count": 1,
        "nicosserver.bifrost.service.unknown.logs.level.input.count": 1,
        "nicosserver.bifrost.service.unknown.logs.level.warning.count": 1,
        "nicosserver.bifrost.service.unknown.logs.level.error.count": 1,
        "nicosserver.bifrost.service.unknown.logs.level.critical.count": 1,
    }
    for metric, count in expected_counts.items():
        assert metrics[metric] == (count, FIXED_TIMESTAMP)

    handler.close()
    assert client.flush_calls == 1
    assert client.closed


def test_carbon_log_level_counter_handler_emits_service_specific_metrics():
    client = CapturingClient()
    handler = CarbonLogLevelCounterHandler(
        instrument="YMIR",
        prefix="nicosserver",
        service_name="daemon",
        client=client,
        flush_interval_s=999,
        heartbeat_interval_s=0,
        start_heartbeat_thread=False,
        time_fn=lambda: FIXED_TIMESTAMP,
    )
    handler.emit(_make_record(logging.INFO))
    handler.flush()

    metrics = _parse_metrics(client.sent_batches[0])
    assert metrics["nicosserver.ymir.service.daemon.logs.level.info.count"] == (
        1,
        FIXED_TIMESTAMP,
    )
    assert metrics["nicosserver.ymir.service.daemon.logs.total.count"] == (
        1,
        FIXED_TIMESTAMP,
    )
    handler.close()


def test_emit_heartbeat_uses_service_metric_root():
    client = CapturingClient()
    handler = CarbonLogLevelCounterHandler(
        instrument="YMIR",
        prefix="nicosserver",
        service_name="cache",
        client=client,
        flush_interval_s=999,
        heartbeat_interval_s=0,
        start_heartbeat_thread=False,
        time_fn=lambda: FIXED_TIMESTAMP + 10,
    )
    handler.emit_heartbeat()
    assert len(client.sent_batches) == 1
    metrics = _parse_metrics(client.sent_batches[0])
    assert metrics["nicosserver.ymir.service.cache.telemetry.heartbeat"] == (
        1,
        FIXED_TIMESTAMP + 10,
    )
    handler.close()


def test_log_counts_flush_automatically_after_interval():
    client = CapturingClient()
    handler = CarbonLogLevelCounterHandler(
        instrument="YMIR",
        prefix="nicosserver",
        service_name="daemon",
        client=client,
        flush_interval_s=0.05,
        heartbeat_interval_s=0,
        start_heartbeat_thread=False,
        time_fn=lambda: FIXED_TIMESTAMP + 20,
    )

    handler.emit(_make_record(logging.INFO))

    assert _wait_until(lambda: bool(client.sent_batches))

    metrics = _parse_metrics(client.sent_batches[0])
    assert metrics["nicosserver.ymir.service.daemon.logs.total.count"] == (
        1,
        FIXED_TIMESTAMP + 20,
    )
    assert metrics["nicosserver.ymir.service.daemon.logs.level.info.count"] == (
        1,
        FIXED_TIMESTAMP + 20,
    )
    handler.close()


def test_idle_log_handler_does_not_emit_empty_windows():
    client = CapturingClient()
    handler = CarbonLogLevelCounterHandler(
        instrument="YMIR",
        prefix="nicosserver",
        service_name="daemon",
        client=client,
        flush_interval_s=0.05,
        heartbeat_interval_s=0,
        start_heartbeat_thread=False,
    )

    time.sleep(0.1)

    assert client.sent_batches == []
    handler.close()


def test_create_carbon_log_handlers_disabled_by_default():
    handlers = create_carbon_log_handlers(SimpleNamespace())
    assert handlers == []


def test_create_carbon_log_handlers_requires_host_when_enabled():
    cfg = SimpleNamespace(telemetry_enabled=True, instrument="bifrost")
    with pytest.raises(ConfigurationError):
        create_carbon_log_handlers(cfg)


def test_create_carbon_log_handlers_enabled():
    cfg = SimpleNamespace(
        telemetry_enabled="true",
        telemetry_carbon_host="127.0.0.1",
        telemetry_carbon_port="2003",
        telemetry_prefix="nicosserver",
        instrument="bifrost",
        telemetry_flush_interval_s="5",
    )
    handlers = create_carbon_log_handlers(cfg)
    assert len(handlers) == 1
    assert isinstance(handlers[0], CarbonLogLevelCounterHandler)
    handlers[0].close()


def test_build_carbon_log_handlers_uses_explicit_service_name(monkeypatch):
    client = CapturingClient()
    monkeypatch.setattr(CarbonConfig, "create_client", lambda self: client)
    cfg = CarbonConfig(
        host="carbon.local",
        instrument="bifrost",
        prefix="nicosserver",
        flush_interval_s=5.0,
        heartbeat_interval_s=0.0,
    )
    handlers = build_carbon_log_handlers(cfg, service_name="poller")
    assert len(handlers) == 1

    handler = handlers[0]
    handler.emit(_make_record(logging.INFO))
    handler.flush()

    metrics = _parse_metrics(client.sent_batches[0])
    assert metrics["nicosserver.bifrost.service.poller.logs.level.info.count"][0] == 1
    handler.close()


def test_package_get_log_handlers_hook_returns_handlers():
    cfg = SimpleNamespace(
        telemetry_enabled=True,
        telemetry_carbon_host="127.0.0.1",
        instrument="bifrost",
    )
    handlers = nicos_ess.get_log_handlers(cfg)
    assert len(handlers) == 1
    assert isinstance(handlers[0], CarbonLogLevelCounterHandler)
    handlers[0].close()
