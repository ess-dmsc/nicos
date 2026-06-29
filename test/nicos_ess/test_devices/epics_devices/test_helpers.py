from types import SimpleNamespace

import pytest

from nicos_ess.devices.epics.pva.epics_common import (
    EpicsChannelKind,
    EpicsMappedChoiceSupport,
    EpicsParameters,
    get_from_cache_or,
)
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsReadable,
)


class TestHelpers:
    class CacheProbe:
        def __init__(self, value=Ellipsis):
            self.value = value
            self.calls = []

        def get(self, dev, key, default=None, mintime=None):
            self.calls.append((dev, key, default, mintime))
            if self.value is Ellipsis:
                return default
            return self.value

    def test_channel_kind_enum_values_are_stable(self):
        assert EpicsChannelKind.READBACK.value == "readback"
        assert EpicsChannelKind.SETPOINT.value == "setpoint"
        assert EpicsChannelKind.STATUS.value == "status"
        assert EpicsChannelKind.COMMAND.value == "command"

    def test_get_from_cache_or_prefers_cache_when_monitor_enabled(self):
        called = {"count": 0}
        cache = self.CacheProbe(123)
        device = SimpleNamespace(
            monitor=True,
            _name="dummy",
            _cache=cache,
        )

        def fallback():
            called["count"] += 1
            return 999

        result = get_from_cache_or(device, "value", fallback)

        assert result == 123
        assert called["count"] == 0
        assert cache.calls == [("dummy", "value", Ellipsis, None)]

    def test_get_from_cache_or_returns_cached_none_as_value(self):
        called = {"count": 0}
        device = SimpleNamespace(
            monitor=True,
            _name="dummy",
            _cache=self.CacheProbe(None),
        )

        def fallback():
            called["count"] += 1
            return 777

        result = get_from_cache_or(device, "value", fallback)

        assert result is None
        assert called["count"] == 0

    def test_get_from_cache_or_uses_fallback_when_cache_is_missing(self):
        called = {"count": 0}
        device = SimpleNamespace(
            monitor=True,
            _name="dummy",
            _cache=self.CacheProbe(),
        )

        def fallback():
            called["count"] += 1
            return 777

        result = get_from_cache_or(device, "value", fallback)

        assert result == 777
        assert called["count"] == 1

    def test_get_from_cache_or_maxage_zero_uses_fallback(self):
        called = {"count": 0}
        device = SimpleNamespace(
            monitor=True,
            _name="dummy",
            _cache=self.CacheProbe(123),
        )

        def fallback():
            called["count"] += 1
            return 777

        result = get_from_cache_or(device, "value", fallback, maxage=0)

        assert result == 777
        assert called["count"] == 1
        assert device._cache.calls == []

    def test_get_from_cache_or_maxage_none_accepts_cache_without_mintime(self):
        device = SimpleNamespace(
            monitor=True,
            _name="dummy",
            _cache=self.CacheProbe(123),
        )

        result = get_from_cache_or(device, "value", lambda: 777, maxage=None)

        assert result == 123
        assert device._cache.calls == [("dummy", "value", Ellipsis, None)]

    def test_get_from_cache_or_positive_maxage_passes_mintime(self):
        device = SimpleNamespace(
            monitor=True,
            _name="dummy",
            _cache=self.CacheProbe(),
        )

        result = get_from_cache_or(device, "value", lambda: 777, maxage=5)

        assert result == 777
        assert len(device._cache.calls) == 1
        assert isinstance(device._cache.calls[0][3], float)

    @pytest.mark.parametrize("mapping_channel", ["read", "write"])
    def test_update_mapped_choices_builds_mapping_and_inverse(
        self, fake_backend, mapping_channel
    ):
        expected_pv = {"read": "PV:READ", "write": "PV:WRITE"}[mapping_channel]
        fake_backend.value_choices[expected_pv] = ["OFF", "ON", "ERROR"]
        mapped_device = SimpleNamespace(
            readpv="PV:READ",
            writepv="PV:WRITE",
            mapping={},
            _inverse_mapping={},
            _mapping_channel=mapping_channel,
            fallback=None,
        )

        def get_channel_value_choices(channel):
            pv = {"read": mapped_device.readpv, "write": mapped_device.writepv}
            return fake_backend.get_value_choices(pv[channel])

        def pv_name_for(channel):
            return {"read": mapped_device.readpv, "write": mapped_device.writepv}[
                channel
            ]

        mapped_device._epics = SimpleNamespace(
            get_channel_value_choices=get_channel_value_choices,
            pv_name_for=pv_name_for,
        )

        def set_ro_param(name, value):
            setattr(mapped_device, name, value)

        mapped_device._setROParam = set_ro_param

        EpicsMappedChoiceSupport._update_mapped_choices(mapped_device)

        assert mapped_device.mapping == {"OFF": 0, "ON": 1, "ERROR": 2}
        assert mapped_device._inverse_mapping == {0: "OFF", 1: "ON", 2: "ERROR"}


class TestEpicsParameters:
    """Contract tests for shared EPICS parameter defaults."""

    def test_parameter_defaults_are_visible_on_device_instances(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 2.5

        device = device_harness.create(
            "daemon",
            EpicsReadable,
            name="readable",
            readpv=readpv,
            monitor=False,
        )

        assert device.epicstimeout == 3.0
        assert device.monitor is False
        assert device.pva is True
        assert device.pollinterval is None
        assert device.maxage is None

    def test_epics_parameters_define_expected_public_parameter_names(self):
        assert {"epicstimeout", "monitor", "pva"} <= set(EpicsParameters.parameters)
