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

"""Harness tests for nicos_ess.devices.metrics_forwarder."""

import pytest

from nicos.core import ConfigurationError

from nicos_ess.devices import metrics_forwarder
from nicos_ess.devices.metrics_forwarder import CarbonForwarder
from nicos_ess.telemetry.config import CarbonConfig
from nicos_ess.telemetry.metrics import SCRIPTS_KEY


class RecordingEmitter:
    def __init__(
        self,
        client=None,
        prefix=None,
        instrument=None,
        flush_interval_s=None,
    ):
        self.client = client
        self.prefix = prefix
        self.instrument = instrument
        self.flush_interval_s = flush_interval_s
        self.calls = []
        self.close_calls = 0

    def process_cache_update(self, timestamp, key, value):
        self.calls.append((timestamp, key, value))
        return []

    def close(self):
        self.close_calls += 1


class TestCarbonForwarderHarness:
    def test_do_init_sets_default_filter_and_empty_emitter(
        self, daemon_device_harness
    ):
        device = daemon_device_harness.create_master(CarbonForwarder)

        assert device._emitter is None
        assert device._checkKey(SCRIPTS_KEY)
        assert device._checkKey("motor/value")
        assert not device._checkKey("motor/target")

    def test_start_worker_disabled_resets_emitter(
        self, daemon_device_harness, monkeypatch
    ):
        device = daemon_device_harness.create_master(CarbonForwarder)
        device._emitter = RecordingEmitter()
        monkeypatch.setattr(
            metrics_forwarder, "read_carbon_config", lambda _cfg: None
        )

        device._startWorker()

        assert device._emitter is None

    def test_start_worker_builds_emitter_from_config(
        self, daemon_device_harness, monkeypatch
    ):
        cfg = CarbonConfig(
            host="carbon.local",
            port=2004,
            prefix="nicos",
            instrument="ymir",
        )
        client = object()
        created = {}
        device = daemon_device_harness.create_master(CarbonForwarder)

        monkeypatch.setattr(
            metrics_forwarder, "read_carbon_config", lambda _cfg: cfg
        )
        monkeypatch.setattr(
            metrics_forwarder, "create_carbon_client", lambda _cfg: client
        )

        def make_emitter(
            client_arg, prefix_arg, instrument_arg, *, flush_interval_s=None
        ):
            emitter = RecordingEmitter(
                client_arg,
                prefix_arg,
                instrument_arg,
                flush_interval_s=flush_interval_s,
            )
            created["emitter"] = emitter
            return emitter

        monkeypatch.setattr(metrics_forwarder, "CacheMetricsEmitter", make_emitter)

        device._startWorker()

        assert device._emitter is created["emitter"]
        assert created["emitter"].client is client
        assert created["emitter"].prefix == "nicos"
        assert created["emitter"].instrument == "ymir"
        assert created["emitter"].flush_interval_s == cfg.flush_interval_s

    def test_start_worker_propagates_config_errors(
        self, daemon_device_harness, monkeypatch
    ):
        device = daemon_device_harness.create_master(CarbonForwarder)

        def raise_config_error(_cfg):
            raise ConfigurationError("bad telemetry config")

        monkeypatch.setattr(
            metrics_forwarder, "read_carbon_config", raise_config_error
        )

        with pytest.raises(ConfigurationError):
            device._startWorker()

    def test_put_change_delegates_matching_updates(self, daemon_device_harness):
        device = daemon_device_harness.create_master(CarbonForwarder)
        emitter = RecordingEmitter()
        device._emitter = emitter

        device._putChange("1710000000", "", SCRIPTS_KEY, "=", "[]")

        assert emitter.calls == [("1710000000", SCRIPTS_KEY, "[]")]

    def test_put_change_ignores_unmatched_keys(self, daemon_device_harness):
        device = daemon_device_harness.create_master(CarbonForwarder)
        emitter = RecordingEmitter()
        device._emitter = emitter

        device._putChange("1710000000", "", "motor/target", "=", "42")

        assert emitter.calls == []

    def test_put_change_delegates_value_updates(self, daemon_device_harness):
        device = daemon_device_harness.create_master(CarbonForwarder)
        emitter = RecordingEmitter()
        device._emitter = emitter

        device._putChange("1710000000", "", "motor/value", "=", "42")

        assert emitter.calls == [("1710000000", "motor/value", "42")]

    def test_put_change_logs_and_swallows_emitter_errors(
        self, daemon_device_harness, monkeypatch
    ):
        device = daemon_device_harness.create_master(CarbonForwarder)
        warnings = []

        class FailingEmitter:
            def process_cache_update(self, timestamp, key, value):
                raise RuntimeError("boom")

        device._emitter = FailingEmitter()
        monkeypatch.setattr(
            device.log,
            "warning",
            lambda *args, **kwargs: warnings.append((args, kwargs)),
        )

        device._putChange("1710000000", "", SCRIPTS_KEY, "=", "[]")

        assert warnings == [
            (("Could not forward telemetry update for %s", SCRIPTS_KEY), {"exc": 1})
        ]

    def test_shutdown_closes_emitter_once_and_clears_reference(
        self, daemon_device_harness
    ):
        device = daemon_device_harness.create_master(CarbonForwarder)
        emitter = RecordingEmitter()
        device._emitter = emitter

        device.doShutdown()
        device.doShutdown()

        assert emitter.close_calls == 1
        assert device._emitter is None
