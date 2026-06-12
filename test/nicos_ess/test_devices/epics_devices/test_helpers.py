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

from types import SimpleNamespace

import pytest

from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsReadable,
)
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsParameters,
    PvReadOrWrite,
    RecordType,
    _update_mapped_choices,
    get_from_cache_or,
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

    def test_record_type_enum_values_are_stable(self):
        assert RecordType.VALUE.value == 1
        assert RecordType.STATUS.value == 2
        assert RecordType.BOTH.value == 3

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

    @pytest.mark.parametrize(
        "selector,expected_pv",
        [(PvReadOrWrite.readpv, "PV:READ"), (PvReadOrWrite.writepv, "PV:WRITE")],
    )
    def test_update_mapped_choices_builds_mapping_and_inverse(
        self, fake_backend, selector, expected_pv
    ):
        fake_backend.value_choices[expected_pv] = ["OFF", "ON", "ERROR"]
        mapped_device = SimpleNamespace(
            readpv="PV:READ",
            writepv="PV:WRITE",
            mapping={},
            _inverse_mapping={},
            fallback=None,
        )

        def get_value_choices(field):
            return fake_backend.get_value_choices(getattr(mapped_device, field))

        mapped_device._epics = SimpleNamespace(get_value_choices=get_value_choices)

        def set_ro_param(name, value):
            setattr(mapped_device, name, value)

        mapped_device._setROParam = set_ro_param

        _update_mapped_choices(mapped_device, selector)

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
