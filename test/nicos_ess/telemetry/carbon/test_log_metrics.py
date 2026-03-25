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
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

"""Tests for Carbon-backed log metric handlers."""

import logging
from types import SimpleNamespace

import pytest

import nicos_ess
from nicos.core import ConfigurationError
from nicos.utils.loggers import ACTION, INPUT
from nicos_ess.telemetry.carbon.log_metrics import (
    CarbonLogLevelCounterHandler,
    build_carbon_log_handlers,
    create_carbon_log_handlers,
)

FIXED_TIMESTAMP = 1773070701 # Arbitrary fixed timestamp


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


def test_carbon_log_level_counter_handler_emits_expected_metrics():
    clock = FakeClock(100)
    client = CapturingClient()
    handler = CarbonLogLevelCounterHandler(
        instrument="BIFROST",
        prefix="nicos",
        client=client,
        flush_interval_s=999,
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
        "nicos.bifrost.service.unknown.logs.total.count": 7,
        "nicos.bifrost.service.unknown.logs.level.debug.count": 1,
        "nicos.bifrost.service.unknown.logs.level.info.count": 1,
        "nicos.bifrost.service.unknown.logs.level.action.count": 1,
        "nicos.bifrost.service.unknown.logs.level.input.count": 1,
        "nicos.bifrost.service.unknown.logs.level.warning.count": 1,
        "nicos.bifrost.service.unknown.logs.level.error.count": 1,
        "nicos.bifrost.service.unknown.logs.level.critical.count": 1,
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
        telemetry_prefix="nicos",
        instrument="bifrost",
        telemetry_flush_interval_s="5",
    )
    handlers = create_carbon_log_handlers(cfg)
    assert len(handlers) == 1
    assert isinstance(handlers[0], CarbonLogLevelCounterHandler)
    handlers[0].close()


def test_build_carbon_log_handlers_uses_explicit_service_name():
    cfg = SimpleNamespace(
        create_client=lambda: CapturingClient(),
        instrument="bifrost",
        prefix="nicos",
        flush_interval_s=5.0,
        heartbeat_interval_s=0.0,
    )
    handlers = build_carbon_log_handlers(cfg, service_name="poller")
    assert len(handlers) == 1

    handler = handlers[0]
    handler.emit(_make_record(logging.INFO))
    handler.flush()

    metrics = _parse_metrics(handler.client.sent_batches[0])
    assert metrics["nicos.bifrost.service.poller.logs.level.info.count"][0] == 1
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
