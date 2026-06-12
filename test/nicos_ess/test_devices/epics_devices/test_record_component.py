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

"""Unit tests for the EPICS component and the device glue, without a NICOS
session or harness.

``EpicsChannelComponent`` is pure mechanism and is tested with just a fake
wrapper. The ``EpicsDeviceBase`` cache/status glue is tested by borrowing
its methods onto a duck-typed probe object. Neither covers the daemon/poller
cache-key contract -- that stays with the harness tests.
"""

from dataclasses import FrozenInstanceError

import pytest

from nicos.core import ConfigurationError, status
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    EpicsChannelComponent,
    EpicsChannelInfo,
    EpicsChannelRole,
    resolve_channel_pv_names,
)
from nicos_ess.devices.epics.pva.epics_multisource import (
    EpicsMultiSourceBase,
    EpicsMultiSourceComponent,
)
from test.nicos_ess.test_devices.doubles.epics_pva_backend import (
    FakeEpicsBackend,
)


class StubLog:
    def __init__(self):
        self.messages = []

    def _record(self, level, msg, *args):
        self.messages.append((level, msg % args if args else msg))

    def debug(self, msg, *args):
        self._record("debug", msg, *args)

    def info(self, msg, *args):
        self._record("info", msg, *args)

    def warning(self, msg, *args):
        self._record("warning", msg, *args)

    def error(self, msg, *args):
        self._record("error", msg, *args)


EPICS_CHANNELS = {
    "value": EpicsChannelInfo("value", ".RBV", EpicsChannelRole.VALUE_AND_STATUS),
    "target": EpicsChannelInfo("target", ".VAL", EpicsChannelRole.VALUE),
    "moving": EpicsChannelInfo("", ".MOVN", EpicsChannelRole.STATUS),
    "speed": EpicsChannelInfo("", ".VELO", EpicsChannelRole.VALUE),
    "label": EpicsChannelInfo("", ".DESC", EpicsChannelRole.VALUE, as_string=True),
}

PV_NAMES = {
    "value": "SIM:M1.RBV",
    "target": "SIM:M1.VAL",
    "moving": "SIM:M1.MOVN",
    "speed": "SIM:M1.VELO",
    "label": "SIM:M1.DESC",
}


class TestEpicsChannelInfo:
    def test_defaults_and_frozen_fields(self):
        info = EpicsChannelInfo("value", ".RBV", EpicsChannelRole.VALUE_AND_STATUS)
        assert info.as_string is False
        assert info.pv_root_attr is None
        assert info.pv_attr is None
        assert info.subscribe is True

        try:
            info.cache_key = "other"
        except FrozenInstanceError:
            pass
        else:
            raise AssertionError("EpicsChannelInfo must be immutable")


def make_component(epics_channels=None, pv_names_by_channel=None):
    backend = FakeEpicsBackend()
    component = EpicsChannelComponent(
        EPICS_CHANNELS if epics_channels is None else epics_channels,
        PV_NAMES if pv_names_by_channel is None else pv_names_by_channel,
        wrapper=backend,
    )
    return component, backend


class TestPvResolution:
    def test_pv_name_for_is_a_lookup(self):
        component, _ = make_component()
        assert component.pv_name_for("value") == "SIM:M1.RBV"
        assert component.pv_name_for("unknown_channel") is None

    def test_resolve_channel_pv_names_supports_mixed_roots(self):
        class Device:
            detectorpv = "DET:"
            imagepv = "IMG:"
            vacpv = "VAC:PRESS"
            directpv = "DIRECT:PV"

        channels = {
            "state": EpicsChannelInfo("", "State", EpicsChannelRole.STATUS),
            "image": EpicsChannelInfo(
                "", "ArrayData", EpicsChannelRole.VALUE, pv_root_attr="imagepv"
            ),
            "vacuum": EpicsChannelInfo(
                "", "", EpicsChannelRole.STATUS, pv_root_attr="vacpv"
            ),
            "direct": EpicsChannelInfo(
                "", "", EpicsChannelRole.VALUE, pv_attr="directpv"
            ),
            "unset_optional": EpicsChannelInfo(
                "", "", EpicsChannelRole.VALUE, pv_attr="missingpv", optional=True
            ),
        }

        assert resolve_channel_pv_names(Device(), channels, "detectorpv") == {
            "state": "DET:State",
            "image": "IMG:ArrayData",
            "vacuum": "VAC:PRESS",
            "direct": "DIRECT:PV",
            "unset_optional": None,
        }

    def test_resolve_channel_pv_names_rejects_unresolved_required_channel(self):
        class Device:
            name = "probe"

        channels = {
            "value": EpicsChannelInfo("", ".RBV", EpicsChannelRole.VALUE),
        }

        with pytest.raises(ConfigurationError):
            resolve_channel_pv_names(Device(), channels, "motorpv")

    def test_cache_key_for_prefers_channel_info(self):
        component, _ = make_component()
        assert component.cache_key_for("value") == "value"
        assert component.cache_key_for("moving") == "moving"
        assert component.cache_key_for("not_a_channel") == "not_a_channel"

    def test_pvs_to_connect_skips_missing_and_deduplicates(self):
        pv_names_by_channel = dict(PV_NAMES, label=None, speed="SIM:M1.RBV")
        component, _ = make_component(pv_names_by_channel=pv_names_by_channel)
        pvs = component.pvs_to_connect()
        assert pvs.count("SIM:M1.RBV") == 1
        assert None not in pvs
        assert set(pvs) == {"SIM:M1.RBV", "SIM:M1.VAL", "SIM:M1.MOVN"}

    def test_connect_connects_every_pv(self):
        component, backend = make_component()
        component.connect()
        assert set(backend.connect_calls) == set(PV_NAMES.values())

    def test_connect_in_simulation_does_not_touch_pvs(self):
        component, backend = make_component()
        component.connect(simulation=True)
        assert backend.connect_calls == []

    def test_connect_keeps_the_injected_wrapper(self):
        component, backend = make_component()
        component.connect()
        assert component.wrapper is backend


class TestSubscriptions:
    def callback(self, *args, **kwargs):
        pass

    def test_subscribe_channels_subscribes_each_channel(self):
        component, backend = make_component()
        component.connect()
        component.subscribe_channels(self.callback)
        subscribed = {pv for pv, *_ in backend.subscriptions}
        assert subscribed == set(PV_NAMES.values())

    def test_subscribe_channels_skips_unsubscribed_channels(self):
        channels = dict(
            EPICS_CHANNELS,
            speed=EpicsChannelInfo(
                "", ".VELO", EpicsChannelRole.VALUE, subscribe=False
            ),
        )
        component, backend = make_component(epics_channels=channels)
        component.connect()
        component.subscribe_channels(self.callback)
        subscribed = {pv for pv, *_ in backend.subscriptions}
        assert "SIM:M1.VELO" not in subscribed

    def test_unsubscribed_channel_still_connects_and_reads_on_demand(self):
        channels = dict(
            EPICS_CHANNELS,
            speed=EpicsChannelInfo(
                "", ".VELO", EpicsChannelRole.VALUE, subscribe=False
            ),
        )
        component, backend = make_component(epics_channels=channels)
        backend.values["SIM:M1.VELO"] = 7.5

        component.connect()
        component.subscribe_channels(self.callback)

        subscribed = {pv for pv, *_ in backend.subscriptions}
        assert "SIM:M1.VELO" in backend.connect_calls
        assert "SIM:M1.VELO" not in subscribed
        assert component.get_channel_value("speed") == 7.5

    def test_subscribe_channel_honours_as_string_from_channel_info(self):
        component, backend = make_component()
        component.connect()
        component.subscribe_channel("label", self.callback)
        ((_, _, _, _, as_string),) = backend.subscriptions
        assert as_string is True

    def test_subscribe_channel_without_pv_is_a_noop(self):
        component, backend = make_component(
            pv_names_by_channel=dict(PV_NAMES, label=None)
        )
        component.connect()
        assert component.subscribe_channel("label", self.callback) is None
        assert backend.subscriptions == []

    def test_shutdown_closes_every_subscription(self):
        component, backend = make_component()
        component.connect()
        component.subscribe_channels(self.callback)
        assert len(backend.subscriptions) == len(PV_NAMES)
        component.shutdown()
        assert backend.subscriptions == []
        assert component.subscriptions == []


class TestReadsAndWrites:
    def test_get_channel_value_uses_as_string_from_channel_info(self):
        component, backend = make_component()
        component.connect()
        backend.values["SIM:M1.DESC"] = b"motor"
        assert component.get_channel_value("label") == "motor"

    def test_put_channel_value_writes_the_resolved_pv(self):
        component, backend = make_component()
        component.connect()
        component.put_channel_value("target", 42.0)
        assert backend.values["SIM:M1.VAL"] == 42.0


class TestWaitFor:
    def test_returns_immediately_when_already_matching(self):
        component, backend = make_component()
        component.connect()
        backend.values["SIM:M1.MOVN"] = 0
        component.wait_for("moving", 0, timeout=0.1)
        # The temporary subscription is cleaned up again.
        assert component.subscriptions == []
        assert backend.subscriptions == []

    def test_completes_when_a_monitor_update_matches(self):
        component, backend = make_component()
        component.connect()
        backend.values["SIM:M1.MOVN"] = 1

        original_get = backend.get_pv_value

        def get_and_update(pvname, as_string=False):
            # Simulate the value changing right after the initial check.
            result = original_get(pvname, as_string)
            backend.emit_update(pvname, value=0)
            return result

        backend.get_pv_value = get_and_update
        component.wait_for("moving", 0, timeout=1.0)
        assert backend.subscriptions == []

    def test_times_out(self):
        component, backend = make_component()
        component.connect()
        backend.values["SIM:M1.MOVN"] = 1
        try:
            component.wait_for("moving", 0, timeout=0.05)
        except TimeoutError:
            pass
        else:
            raise AssertionError("expected TimeoutError")
        assert backend.subscriptions == []

    def test_precision_match(self):
        component, backend = make_component()
        component.connect()
        backend.values["SIM:M1.RBV"] = 9.999
        component.wait_for("value", 10.0, timeout=0.1, precision=0.01)


class CacheStub:
    """NICOS-cache shaped recorder."""

    def __init__(self):
        self.data = {}
        self.puts = []

    def put(self, dev, key, value, ts=None):
        self.data[key] = value
        self.puts.append((key, value))

    def get(self, dev, key, default=None, mintime=None):
        return self.data.get(key, default)


class GlueProbe:
    """Duck-typed device exercising the real EpicsDeviceBase glue methods
    without the NICOS device machinery."""

    _value_change_callback = EpicsDeviceBase._value_change_callback
    _connection_change_callback = EpicsDeviceBase._connection_change_callback
    _refresh_status = EpicsDeviceBase._refresh_status
    _read_channel_cached = EpicsDeviceBase._read_channel_cached
    _read_primary_alarm = EpicsDeviceBase._read_primary_alarm
    doStatus = EpicsDeviceBase.doStatus

    _primary_channel = "value"
    monitor = True

    def __init__(self, compute_status=None):
        self._epics, self.backend = make_component()
        self._epics.connect()
        self._epics_channels = self._epics.epics_channels
        self._name = "probe"
        self._cache = CacheStub()
        self.log = StubLog()
        if compute_status is not None:
            self._compute_status = compute_status
        else:
            self._compute_status = lambda maxage=0: (status.OK, "")


class TestDeviceGlue:
    def test_value_change_caches_under_resolved_key(self):
        probe = GlueProbe()
        probe._value_change_callback(
            "SIM:M1.VAL", "target", 42.0, "mm", None, status.OK, ""
        )
        assert probe._cache.data["target"] == 42.0

    def test_primary_channel_also_caches_unit_and_alarm(self):
        probe = GlueProbe()
        probe._value_change_callback(
            "SIM:M1.RBV", "value", 1.0, "mm", None, status.WARN, "hot"
        )
        assert probe._cache.data["value"] == 1.0
        assert probe._cache.data["unit"] == "mm"
        assert probe._cache.data["value_status"] == (status.WARN, "hot")

    def test_status_channel_triggers_status_recompute(self):
        calls = []

        def compute(maxage=0):
            calls.append(maxage)
            return status.BUSY, "moving"

        probe = GlueProbe(compute_status=compute)
        probe._value_change_callback(
            "SIM:M1.MOVN", "moving", 1, "", None, status.OK, ""
        )
        assert calls == [None]
        assert probe._cache.data["status"] == (status.BUSY, "moving")

    def test_value_only_channel_does_not_recompute_status(self):
        def compute(maxage=0):
            raise AssertionError("status must not be recomputed for VALUE channels")

        probe = GlueProbe(compute_status=compute)
        probe._value_change_callback(
            "SIM:M1.VAL", "target", 42.0, "mm", None, status.OK, ""
        )
        assert "status" not in probe._cache.data

    def test_primary_disconnect_caches_lost_epics_connection(self):
        probe = GlueProbe()
        probe._connection_change_callback("SIM:M1.RBV", "value", False)
        assert probe._cache.data["status"] == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )
        assert any(level == "warning" for level, _ in probe.log.messages)

    def test_non_primary_disconnect_is_ignored(self):
        probe = GlueProbe()
        probe._connection_change_callback("SIM:M1.VAL", "target", False)
        assert "status" not in probe._cache.data
        assert probe.log.messages == []

    def test_read_cached_prefers_cache(self):
        probe = GlueProbe()
        probe._cache.data["value"] = 5.5
        assert probe._read_channel_cached("value") == 5.5
        assert probe.backend.get_calls == []

    def test_read_cached_falls_back_to_epics(self):
        probe = GlueProbe()
        probe.backend.values["SIM:M1.RBV"] = 3.25
        assert probe._read_channel_cached("value") == 3.25
        assert probe.backend.get_calls

    def test_read_cached_maxage_zero_always_asks(self):
        probe = GlueProbe()
        probe._cache.data["value"] = 5.5
        probe.backend.values["SIM:M1.RBV"] = 3.25
        assert probe._read_channel_cached("value", maxage=0) == 3.25

    def test_status_reads_cache_unless_freshness_is_forced(self):
        probe = GlueProbe()
        probe._cache.data["status"] = (status.BUSY, "moving")
        # maxage=None serves the cached (monitor-maintained) status;
        # maxage=0 would force a recompute.
        assert probe.doStatus(maxage=None) == (status.BUSY, "moving")

    def test_primary_alarm_timeout_reports_unknown_connection_loss(self):
        probe = GlueProbe()
        probe.backend.disconnect_backend()
        assert probe._read_primary_alarm() == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )


MULTI_CHANNELS = {
    "voltage": EpicsChannelInfo("vmon", "-VMon", EpicsChannelRole.VALUE),
    "power": EpicsChannelInfo("power", "-Pw", EpicsChannelRole.VALUE),
    "status_on": EpicsChannelInfo("", "-Status-ON", EpicsChannelRole.STATUS),
}

SOURCES = {
    "ch0": "SIM:HVM-0:Ch0",
    "ch1": "SIM:HVM-0:Ch1",
}


def make_multi_component():
    backend = FakeEpicsBackend()
    component = EpicsMultiSourceComponent(MULTI_CHANNELS, SOURCES, wrapper=backend)
    return component, backend


class MultiGlueProbe:
    _connection_change_callback = EpicsMultiSourceBase._connection_change_callback
    _source_connection_key = EpicsMultiSourceBase._source_connection_key
    _source_connection_status = EpicsMultiSourceBase._source_connection_status
    _worst_status = staticmethod(EpicsMultiSourceBase._worst_status)
    _compute_status = EpicsMultiSourceBase._compute_status
    _refresh_status = EpicsDeviceBase._refresh_status
    doStatus = EpicsDeviceBase.doStatus

    monitor = True
    sources = SOURCES
    _epics_channels = MULTI_CHANNELS
    _source_connection_cache_key = EpicsMultiSourceBase._source_connection_cache_key

    def __init__(self):
        self._name = "multi_probe"
        self._cache = CacheStub()
        self.log = StubLog()


class TestMultiSource:
    def test_source_pv_is_prefix_plus_suffix(self):
        component, _ = make_multi_component()
        assert component.source_pv("ch1", "voltage") == "SIM:HVM-0:Ch1-VMon"

    def test_source_key_namespaces_per_source(self):
        component, _ = make_multi_component()
        assert component.source_key("ch0", "voltage") == "ch0/vmon"
        assert component.source_key("ch1", "status_on") == "ch1/status_on"

    def test_channel_keys_are_visible_for_device_stale_guard(self):
        component, _ = make_multi_component()
        assert set(component.pv_names_by_channel) == set(MULTI_CHANNELS)

    def test_pvs_to_connect_is_the_cross_product(self):
        component, _ = make_multi_component()
        pvs = component.pvs_to_connect()
        assert len(pvs) == len(SOURCES) * len(MULTI_CHANNELS)
        assert "SIM:HVM-0:Ch0-Pw" in pvs
        assert "SIM:HVM-0:Ch1-Status-ON" in pvs

    def test_subscribe_channels_passes_source_and_channel_as_param(self):
        component, backend = make_multi_component()
        component.connect()
        component.subscribe_channels(lambda *a, **k: None)
        params = {param for _, param, *_ in backend.subscriptions}
        assert ("ch0", "voltage") in params
        assert ("ch1", "status_on") in params
        assert len(params) == len(SOURCES) * len(MULTI_CHANNELS)

    def test_get_source_value_reads_the_source_pv(self):
        component, backend = make_multi_component()
        component.connect()
        backend.values["SIM:HVM-0:Ch1-VMon"] = 999.0
        assert component.get_source_value("ch1", "voltage") == 999.0

    def test_put_source_value_writes_the_source_pv(self):
        component, backend = make_multi_component()
        component.connect()
        component.put_source_value("ch1", "power", 1)
        assert backend.values["SIM:HVM-0:Ch1-Pw"] == 1

    def test_connection_loss_is_part_of_worst_case_status(self):
        probe = MultiGlueProbe()

        probe._connection_change_callback(
            "SIM:HVM-0:Ch1-Status-ON", ("ch1", "status_on"), False
        )

        assert probe.doStatus(maxage=None) == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )
        assert probe.doStatus(maxage=0) == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )

    def test_reconnect_clears_source_connection_loss_status(self):
        probe = MultiGlueProbe()
        probe._connection_change_callback(
            "SIM:HVM-0:Ch1-Status-ON", ("ch1", "status_on"), False
        )

        probe._connection_change_callback(
            "SIM:HVM-0:Ch1-Status-ON", ("ch1", "status_on"), True
        )

        assert probe.doStatus(maxage=None) == (status.OK, "")
