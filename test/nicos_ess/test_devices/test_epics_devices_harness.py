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
#   NICOS contributors
#
# *****************************************************************************

"""Harness tests for all classes in `nicos_ess.devices.epics.pva.epics_devices`.

The tests are intentionally behavior-focused and split by class with explicit
"setup / act / assert" steps for readability and future extension.
"""

from types import SimpleNamespace

import numpy
import pytest

from nicos.core import MoveError, status

from nicos_ess.devices.epics.pva import epics_devices
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsAnalogMoveable,
    EpicsParameters,
    EpicsDigitalMoveable,
    EpicsManualMappedAnalogMoveable,
    EpicsMappedMoveable,
    EpicsMappedReadable,
    EpicsReadable,
    RecordType,
    EpicsStringMoveable,
    EpicsStringReadable,
    PvReadOrWrite,
    _update_mapped_choices,
    get_from_cache_or,
)
from test.nicos_ess.test_devices.doubles.epics_pva_backend import (
    analog_moveable_config,
    mapped_config,
    patch_create_wrapper,
    string_moveable_config,
)


@pytest.fixture
def fake_backend(monkeypatch):
    """Install a reusable fake EPICS backend for each test."""
    return patch_create_wrapper(monkeypatch, epics_devices)


def _manual_moveable_config():
    cfg = analog_moveable_config()
    cfg["mapping"] = {"14 Hz": 14, "28 Hz": 28}
    return cfg


class TestHelpers:
    """Tests for helper functions and enums in the module."""

    def test_record_type_enum_values_are_stable(self):
        assert RecordType.VALUE.value == 1
        assert RecordType.STATUS.value == 2
        assert RecordType.BOTH.value == 3

    def test_get_from_cache_or_prefers_cache_when_monitor_enabled(self):
        called = {"count": 0}
        device = SimpleNamespace(
            monitor=True,
            _name="dummy",
            _cache=SimpleNamespace(get=lambda dev, key: 123),
        )

        def fallback():
            called["count"] += 1
            return 999

        result = get_from_cache_or(device, "value", fallback)

        assert result == 123
        assert called["count"] == 0

    def test_get_from_cache_or_uses_fallback_when_cache_has_no_value(self):
        called = {"count": 0}
        device = SimpleNamespace(
            monitor=True,
            _name="dummy",
            _cache=SimpleNamespace(get=lambda dev, key: None),
        )

        def fallback():
            called["count"] += 1
            return 777

        result = get_from_cache_or(device, "value", fallback)

        assert result == 777
        assert called["count"] == 1

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
            _epics_wrapper=fake_backend,
            mapping={},
            _inverse_mapping={},
        )
        mapped_device._setROParam = lambda name, value: setattr(mapped_device, name, value)

        _update_mapped_choices(mapped_device, selector)

        assert mapped_device.mapping == {"OFF": 0, "ON": 1, "ERROR": 2}
        assert mapped_device._inverse_mapping == {0: "OFF", 1: "ON", 2: "ERROR"}


class TestEpicsParameters:
    """Contract tests for shared EPICS parameter defaults."""

    def test_parameter_defaults_are_visible_on_device_instances(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 2.5

        # Act
        dev = device_harness.create(
            "daemon",
            EpicsReadable,
            name="readable",
            readpv=readpv,
            monitor=False,
        )

        # Assert: values come from EpicsParameters and are inherited by subclasses.
        assert dev.epicstimeout == 3.0
        assert dev.monitor is False
        assert dev.pva is True
        assert dev.pollinterval is None
        assert dev.maxage is None

    def test_epics_parameters_define_expected_public_parameter_names(self):
        # `nexus_config` is inherited from HasNexusConfig.
        assert {"epicstimeout", "monitor", "pva"} <= set(EpicsParameters.parameters)


class TestEpicsReadable:
    """Behavior tests for `EpicsReadable` in daemon/poller/shared-cache roles."""

    def test_daemon_readable_uses_direct_epics_reads_when_monitor_disabled(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 1.23
        fake_backend.units[readpv] = "A"
        fake_backend.alarms[readpv] = (status.WARN, "minor alarm")

        # Act
        dev = device_harness.create(
            "daemon",
            EpicsReadable,
            name="readable",
            readpv=readpv,
            monitor=False,
        )

        # Assert
        assert fake_backend.connect_calls == [readpv]
        assert fake_backend.subscriptions == []
        assert device_harness.run("daemon", dev.read, 0) == 1.23
        assert device_harness.run("daemon", lambda: dev.unit) == "A"
        assert device_harness.run("daemon", dev.status, 0) == (
            status.WARN,
            "minor alarm",
        )

    def test_daemon_readable_status_returns_timeout_error_on_backend_timeout(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 1.0
        fake_backend.get_alarm_status = lambda pv: (_ for _ in ()).throw(TimeoutError())

        dev = device_harness.create(
            "daemon",
            EpicsReadable,
            name="readable",
            readpv=readpv,
            monitor=False,
        )

        # Act + Assert
        assert device_harness.run("daemon", dev.status, 0) == (
            status.ERROR,
            "timeout reading status",
        )

    def test_poller_readable_value_and_status_callbacks_write_cache(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 0.0

        dev = device_harness.create(
            "poller",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )

        # Act
        fake_backend.emit_update(
            readpv,
            value=5.5,
            units="V",
            severity=status.ERROR,
            message="trip",
        )

        # Assert
        assert len(fake_backend.subscriptions) == 2
        assert device_harness.run("poller", dev._cache.get, dev, "value") == 5.5
        assert device_harness.run("poller", dev._cache.get, dev, "unit") == "V"
        assert device_harness.run("poller", dev._cache.get, dev, "status") == (
            status.ERROR,
            "trip",
        )

    def test_poller_readable_connection_callback_sets_comm_failure(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 0.0

        dev = device_harness.create(
            "poller",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )

        # Act
        fake_backend.emit_update(
            readpv,
            value=5.5,
            units="V",
            severity=status.ERROR,
            message="trip",
        )
        fake_backend.emit_connection(readpv, False)

        # Assert
        assert len(fake_backend.subscriptions) == 2
        assert device_harness.run("poller", dev._cache.get, dev, "status") == (
            status.ERROR,
            "communication failure",
        )

    def test_daemon_readable_can_consume_poller_cached_values(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 0.0

        daemon = device_harness.create(
            "daemon",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )

        # Act
        fake_backend.emit_update(readpv, value=8.25, units="A")
        fake_backend.values[readpv] = 99.0  # stale backend value should be ignored

        # Assert
        assert device_harness.run("daemon", daemon.read) == 8.25

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsReadable.read(maxage=0)` should bypass monitor cache and "
            "perform a fresh backend read."
        ),
        strict=False,
    )
    def test_readable_read_maxage_zero_bypasses_cached_value(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:READ"
        fake_backend.values[readpv] = 2.0

        daemon = device_harness.create(
            "daemon",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )
        device_harness.run("poller", daemon._cache.put, daemon._name, "value", 1.0)

        # Act
        observed = device_harness.run("daemon", daemon.read, 0)

        # Assert
        assert observed == 2.0

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsReadable.status(maxage=0)` should bypass monitor cache and "
            "perform a fresh backend alarm read."
        ),
        strict=False,
    )
    def test_readable_status_maxage_zero_bypasses_cached_status(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:READ:STATUS"
        fake_backend.values[readpv] = 0.0
        fake_backend.alarms[readpv] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsReadable.read(maxage>0)` should reject stale cache entries "
            "and refresh from backend."
        ),
        strict=False,
    )
    def test_readable_read_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:READ:POSITIVE"
        fake_backend.values[readpv] = 3.0

        daemon = device_harness.create(
            "daemon",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", 1.0, time=0.0
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0.1)

        # Assert
        assert observed == 3.0

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsReadable.status(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_readable_status_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:READ:STATUS:POSITIVE"
        fake_backend.values[readpv] = 0.0
        fake_backend.alarms[readpv] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
            time=0.0,
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0.1)

        # Assert
        assert observed == (status.WARN, "fresh alarm")


class TestEpicsStringReadable:
    """Behavior tests for string readable EPICS class."""

    def test_string_readable_requests_string_mode_from_backend(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:STR.RBV"
        fake_backend.values[readpv] = "hello"

        dev = device_harness.create(
            "daemon",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
            monitor=False,
        )
        value = device_harness.run("daemon", dev.read, 0)

        assert value == "hello"
        assert ("get_pv_value", readpv, True) in fake_backend.get_calls

    def test_string_readable_converts_char_waveform_in_callback(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:STR.RBV"
        fake_backend.values[readpv] = ""
        dev = device_harness.create(
            "poller",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )

        fake_backend.emit_update(readpv, value=numpy.array([65, 66, 67]), units="")

        assert device_harness.run("poller", dev._cache.get, dev, "value") == "ABC"

    def test_daemon_string_readable_prefers_cached_value_when_monitor_enabled(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:STR.RBV"
        fake_backend.values[readpv] = "backend-before"

        daemon = device_harness.create(
            "daemon",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        fake_backend.emit_update(readpv, value="cached", units="")
        fake_backend.values[readpv] = "backend-after"
        get_calls_before = len(fake_backend.get_calls)

        # Act
        value = device_harness.run("daemon", daemon.read)

        # Assert
        assert value == "cached"
        assert len(fake_backend.get_calls) == get_calls_before

    def test_daemon_string_readable_falls_back_to_backend_without_cached_value(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:STR.RBV"
        fake_backend.values[readpv] = "from-backend"
        dev = device_harness.create(
            "daemon",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        get_calls_before = len(fake_backend.get_calls)

        # Act
        value = device_harness.run("daemon", dev.read, 0)

        # Assert
        assert value == "from-backend"
        assert len(fake_backend.get_calls) == get_calls_before + 1

    def test_daemon_string_readable_ignores_cache_when_monitor_disabled(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:STR.RBV"
        fake_backend.values[readpv] = "from-backend"
        dev = device_harness.create(
            "daemon",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
            monitor=False,
        )
        device_harness.run("daemon", dev._cache.put, dev._name, "value", "from-cache")
        get_calls_before = len(fake_backend.get_calls)

        # Act
        value = device_harness.run("daemon", dev.read, 0)

        # Assert
        assert value == "from-backend"
        assert len(fake_backend.get_calls) == get_calls_before + 1

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsStringReadable.read(maxage=0)` should bypass monitor cache "
            "and perform a fresh backend read."
        ),
        strict=False,
    )
    def test_string_readable_read_maxage_zero_bypasses_cached_value(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:STRREAD"
        fake_backend.values[readpv] = "NEW"

        daemon = device_harness.create(
            "daemon",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", "OLD"
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0)

        # Assert
        assert observed == "NEW"

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsStringReadable.status(maxage=0)` should bypass monitor "
            "cache and perform a fresh backend alarm read."
        ),
        strict=False,
    )
    def test_string_readable_status_maxage_zero_bypasses_cached_status(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:STRREAD:STATUS"
        fake_backend.values[readpv] = "OFF"
        fake_backend.alarms[readpv] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsStringReadable.read(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_string_readable_read_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:STRREAD:POSITIVE"
        fake_backend.values[readpv] = "NEW"

        daemon = device_harness.create(
            "daemon",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", "OLD", time=0.0
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0.1)

        # Assert
        assert observed == "NEW"

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsStringReadable.status(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_string_readable_status_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:STRREAD:STATUS:POSITIVE"
        fake_backend.values[readpv] = "OFF"
        fake_backend.alarms[readpv] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
            time=0.0,
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0.1)

        # Assert
        assert observed == (status.WARN, "fresh alarm")


class TestEpicsAnalogMoveable:
    """Behavior tests for floating moveable class."""

    def test_daemon_analog_moveable_reads_writes_and_status_transitions(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        cfg["monitor"] = False
        fake_backend.values[cfg["readpv"]] = 1.5
        fake_backend.values[cfg["writepv"]] = 1.5
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        fake_backend.limits[cfg["writepv"]] = (-100.0, 100.0)

        # Act
        dev = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.run("daemon", dev.start, 7.0)

        # Assert
        assert fake_backend.connect_calls == [cfg["readpv"], cfg["writepv"]]
        assert fake_backend.put_calls[-1] == (cfg["writepv"], 7.0, False)
        assert device_harness.run("daemon", dev.status, 0)[0] == status.BUSY
        fake_backend.values[cfg["readpv"]] = 7.0
        assert device_harness.run("daemon", dev.status, 0)[0] == status.OK
        assert device_harness.run("daemon", lambda: dev.abslimits) == (
            -100.0,
            100.0,
        )

    def test_daemon_analog_moveable_status_returns_timeout_error_on_backend_timeout(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        cfg["monitor"] = False
        fake_backend.values[cfg["readpv"]] = 1.0
        fake_backend.values[cfg["writepv"]] = 1.0
        fake_backend.get_alarm_status = lambda pv: (_ for _ in ()).throw(TimeoutError())

        dev = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )

        # Act + Assert
        assert device_harness.run("daemon", dev.status, 0) == (
            status.ERROR,
            "timeout reading status",
        )

    def test_poller_analog_moveable_callbacks_cache_target_limits_and_status(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        cfg["targetpv"] = "SIM:M1.TARGET"
        fake_backend.values[cfg["readpv"]] = 2.0
        fake_backend.values[cfg["writepv"]] = 2.0
        fake_backend.values[cfg["targetpv"]] = 2.0
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        dev = device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )

        # Act
        fake_backend.emit_update(
            cfg["readpv"],
            value=3.0,
            units="mm",
            severity=status.WARN,
            message="alarm",
        )
        fake_backend.emit_update(cfg["writepv"], value=3.5, limits=(-10.0, 10.0))
        fake_backend.emit_update(cfg["targetpv"], value=3.5)

        # Assert
        assert len(fake_backend.subscriptions) == 4
        assert device_harness.run("poller", dev._cache.get, dev, "value") == 3.0
        assert device_harness.run("poller", dev._cache.get, dev, "unit") == "mm"
        assert device_harness.run("poller", dev._cache.get, dev, "abslimits") == (
            -10.0,
            10.0,
        )
        assert device_harness.run("poller", dev._cache.get, dev, "target") == 3.5
        assert device_harness.run("poller", dev._cache.get, dev, "status")[0] == (
            status.BUSY
        )

        fake_backend.emit_connection(cfg["readpv"], False)
        assert device_harness.run("poller", dev._cache.get, dev, "status") == (
            status.ERROR,
            "communication failure",
        )

    def test_daemon_analog_moveable_reads_shared_cache_from_poller(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 0.0
        fake_backend.values[cfg["writepv"]] = 0.0
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, 5.0)
        fake_backend.emit_update(cfg["writepv"], value=5.0, limits=(-100.0, 100.0))
        fake_backend.emit_update(cfg["readpv"], value=5.0, units="mm")
        fake_backend.values[cfg["readpv"]] = 999.0

        # Assert
        assert device_harness.run("daemon", daemon.status)[0] == status.OK
        assert device_harness.run("daemon", daemon.read) == 5.0

    def test_move_wait_does_not_complete_from_stale_cached_target_state(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28.0
        fake_backend.values[cfg["writepv"]] = 28.0
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="moveable",
            **cfg,
        )

        # Seed stale cache entries from a previous finished move.
        fake_backend.emit_update(cfg["writepv"], value=28.0, limits=(-100.0, 100.0))
        fake_backend.emit_update(
            cfg["readpv"],
            value=28.0,
            units="mm",
            severity=status.OK,
            message="idle",
        )

        # Act
        device_harness.run("daemon", daemon.start, 14.0)
        completed = device_harness.run("daemon", daemon.isCompleted)
        move_status = device_harness.run("daemon", daemon.status, 0)

        # Assert: must not complete before fresh readback proves target reached.
        assert completed is False
        assert move_status[0] == status.BUSY

    def test_completion_uses_fresh_readback_not_stale_cache(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28.0
        fake_backend.values[cfg["writepv"]] = 28.0
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="moveable",
            **cfg,
        )
        fake_backend.emit_update(cfg["readpv"], value=28.0, units="mm")

        # Act
        device_harness.run("daemon", daemon.start, 14.0)
        fake_backend.values[cfg["readpv"]] = 14.0
        completed = device_harness.run("daemon", daemon.isCompleted)

        # Assert
        assert completed is True

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsAnalogMoveable.read(maxage=0)` should bypass monitor cache "
            "and perform a fresh backend read."
        ),
        strict=False,
    )
    def test_analog_moveable_read_maxage_zero_bypasses_cached_value(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 2.0
        fake_backend.values[cfg["writepv"]] = 2.0

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.run("poller", daemon._cache.put, daemon._name, "value", 1.0)

        # Act
        observed = device_harness.run("daemon", daemon.read, 0)

        # Assert
        assert observed == 2.0

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsAnalogMoveable.status(maxage=0)` should bypass monitor "
            "cache and perform a fresh backend alarm read."
        ),
        strict=False,
    )
    def test_analog_moveable_status_maxage_zero_bypasses_cached_status(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 0.0
        fake_backend.values[cfg["writepv"]] = 0.0
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    @pytest.mark.xfail(
        reason=(
            "TDD: stale `targetpv` callbacks should not overwrite the active "
            "daemon command target for `EpicsAnalogMoveable`."
        ),
        strict=False,
    )
    def test_analog_moveable_stale_target_callback_does_not_replace_active_target(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        cfg["targetpv"] = "SIM:M1.TARGET"
        fake_backend.values[cfg["readpv"]] = 28.0
        fake_backend.values[cfg["writepv"]] = 28.0
        fake_backend.values[cfg["targetpv"]] = 28.0
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, 14.0)
        fake_backend.emit_update(cfg["targetpv"], value=28.0)
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == 14.0

    def test_analog_moveable_second_start_wins_when_old_callbacks_arrive_late(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 0.0
        fake_backend.values[cfg["writepv"]] = 0.0
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, 28.0)
        device_harness.run("daemon", daemon.start, 14.0)
        fake_backend.emit_update(cfg["writepv"], value=28.0, limits=(-100.0, 100.0))
        fake_backend.emit_update(cfg["readpv"], value=28.0, units="mm")
        observed_target = device_harness.run("daemon", lambda: daemon.target)
        observed_status = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert observed_target == 14.0
        assert observed_status[0] == status.BUSY
        assert "14" in observed_status[1]

    @pytest.mark.xfail(
        reason=(
            "TDD: without `targetpv`, stale `writepv` callbacks should not "
            "overwrite falsey active targets for `EpicsAnalogMoveable`."
        ),
        strict=False,
    )
    def test_analog_moveable_falsey_target_survives_stale_write_callback_without_targetpv(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28.0
        fake_backend.values[cfg["writepv"]] = 28.0
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, 0.0)
        fake_backend.emit_update(cfg["writepv"], value=28.0, limits=(-100.0, 100.0))
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == 0.0

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsAnalogMoveable.read(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_analog_moveable_read_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 3.0
        fake_backend.values[cfg["writepv"]] = 3.0

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", 1.0, time=0.0
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0.1)

        # Assert
        assert observed == 3.0

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsAnalogMoveable.status(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_analog_moveable_status_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 0.0
        fake_backend.values[cfg["writepv"]] = 0.0
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
            time=0.0,
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0.1)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    def test_analog_moveable_maw_raises_moveerror_on_disconnect_during_motion(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28.0
        fake_backend.values[cfg["writepv"]] = 28.0
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )

        # Act
        def _disconnect_during_wait():
            from nicos import session as active_session

            original_delay = active_session.delay
            delay_calls = {"count": 0}

            def controlled_delay(seconds):
                delay_calls["count"] += 1
                if delay_calls["count"] == 1:
                    fake_backend.emit_connection(cfg["readpv"], False)
                if delay_calls["count"] > 20:
                    raise RuntimeError("test guard: maw did not fail on disconnect")
                return original_delay(seconds)

            active_session.delay = controlled_delay
            try:
                with pytest.raises(MoveError):
                    daemon.maw(14.0)
            finally:
                active_session.delay = original_delay
            return delay_calls["count"]

        delay_calls = device_harness.run("daemon", _disconnect_during_wait)

        # Assert
        assert delay_calls >= 1

    def test_analog_moveable_maw_recovers_from_transient_disconnect_before_next_poll(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28.0
        fake_backend.values[cfg["writepv"]] = 28.0
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )

        # Act
        def _flap_then_recover():
            from nicos import session as active_session

            original_delay = active_session.delay
            delay_calls = {"count": 0}

            def controlled_delay(seconds):
                delay_calls["count"] += 1
                if delay_calls["count"] == 1:
                    fake_backend.emit_connection(cfg["readpv"], False)
                    fake_backend.emit_connection(cfg["readpv"], True)
                    fake_backend.emit_update(cfg["readpv"], value=14.0, units="mm")
                    fake_backend.emit_update(
                        cfg["writepv"], value=14.0, limits=(-100.0, 100.0)
                    )
                if delay_calls["count"] > 20:
                    raise RuntimeError("test guard: maw did not recover")
                return original_delay(seconds)

            active_session.delay = controlled_delay
            try:
                return daemon.maw(14.0), delay_calls["count"]
            finally:
                active_session.delay = original_delay

        value, delay_calls = device_harness.run("daemon", _flap_then_recover)

        # Assert
        assert delay_calls >= 1
        assert value == 14.0

    def test_analog_moveable_error_alarm_takes_precedence_and_aborts_completion(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28.0
        fake_backend.values[cfg["writepv"]] = 28.0
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.run("daemon", daemon.start, 14.0)
        fake_backend.alarms[cfg["readpv"]] = (status.ERROR, "trip")

        # Act + Assert
        assert device_harness.run("daemon", daemon.status, 0)[0] == status.ERROR
        with pytest.raises(MoveError):
            device_harness.run("daemon", daemon.isCompleted)

    @pytest.mark.xfail(
        reason=(
            "TDD: while moving, warning alarms should not cause wait logic to "
            "treat the move as completed."
        ),
        strict=False,
    )
    def test_analog_moveable_warn_alarm_while_moving_does_not_complete_wait(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28.0
        fake_backend.values[cfg["writepv"]] = 28.0
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.run("daemon", daemon.start, 14.0)
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "limit warning")

        # Act
        observed_status = device_harness.run("daemon", daemon.status, 0)
        completed = device_harness.run("daemon", daemon.isCompleted)

        # Assert
        assert observed_status[0] == status.BUSY
        assert completed is False

    def test_analog_moveable_out_of_order_callbacks_keep_busy_until_readback_arrives(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28.0
        fake_backend.values[cfg["writepv"]] = 28.0
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, 14.0)
        fake_backend.emit_update(cfg["writepv"], value=14.0, limits=(-100.0, 100.0))
        status_after_write = device_harness.run("daemon", daemon.status, 0)
        fake_backend.emit_update(cfg["readpv"], value=14.0, units="mm")
        status_after_read = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert status_after_write[0] == status.BUSY
        assert status_after_read[0] == status.OK

    def test_analog_moveable_finish_warns_if_target_not_reached(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        cfg["monitor"] = False
        fake_backend.values[cfg["readpv"]] = 28.0
        fake_backend.values[cfg["writepv"]] = 28.0
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **cfg,
        )
        device_harness.run("daemon", daemon.start, 14.0)

        # Act
        def _finish_and_capture_warning():
            messages = []
            original_warning = daemon.log.warning

            def capture_warning(msg, *args, **kwargs):
                del kwargs
                messages.append(msg % args if args else msg)

            daemon.log.warning = capture_warning
            try:
                daemon.finish()
            finally:
                daemon.log.warning = original_warning
            return messages

        warning_messages = device_harness.run("daemon", _finish_and_capture_warning)

        # Assert
        assert any("did not reach target" in msg for msg in warning_messages)

    @pytest.mark.xfail(
        reason=(
            "TDD: maw can complete incorrectly or stall when daemon relies on stale "
            "poller cache right after start; completion should depend on fresh readback."
        ),
        strict=False,
    )
    def test_analog_maw_waits_until_fresh_readback_reaches_new_target(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28.0
        fake_backend.values[cfg["writepv"]] = 28.0
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="moveable",
            **cfg,
        )

        # Seed stale cache from previous cycle.
        fake_backend.emit_update(cfg["writepv"], value=28.0, limits=(-100.0, 100.0))
        fake_backend.emit_update(cfg["readpv"], value=28.0, units="mm")

        # Act
        def _run_maw_with_delayed_readback():
            from nicos import session as active_session

            original_delay = active_session.delay
            delay_calls = {"count": 0}

            def controlled_delay(seconds):
                delay_calls["count"] += 1
                if delay_calls["count"] == 1:
                    # Simulate readback update that arrives after wait loop starts.
                    fake_backend.values[cfg["readpv"]] = 14.0
                # Safety guard to avoid an endless loop in known buggy behavior.
                if delay_calls["count"] > 30:
                    raise RuntimeError("test guard: maw did not converge")
                return original_delay(seconds)

            active_session.delay = controlled_delay
            try:
                value = daemon.maw(14.0)
            finally:
                active_session.delay = original_delay
            return value, delay_calls["count"]

        final_value, delay_calls = device_harness.run(
            "daemon",
            _run_maw_with_delayed_readback,
        )

        # Assert: must actually wait at least one cycle and return the new value.
        assert delay_calls >= 1
        assert final_value == 14.0


class TestEpicsDigitalMoveable:
    """Behavior tests for integer moveable variant."""

    def test_digital_moveable_converts_start_target_to_int(
        self, device_harness, fake_backend
    ):
        cfg = analog_moveable_config()
        cfg["monitor"] = False
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.limits[cfg["writepv"]] = (-10, 10)

        dev = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.run("daemon", dev.start, "7")

        assert fake_backend.put_calls[-1] == (cfg["writepv"], 7, False)
        assert isinstance(fake_backend.put_calls[-1][1], int)
        assert device_harness.run("daemon", lambda: dev.fmtstr) == "%d"

    def test_move_wait_does_not_complete_from_stale_cached_target_state(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )

        # Seed stale cache entries from a previous finished move.
        fake_backend.emit_update(cfg["writepv"], value=28, limits=(-100, 100))
        fake_backend.emit_update(
            cfg["readpv"],
            value=28,
            units="mm",
            severity=status.OK,
            message="idle",
        )

        # Act
        device_harness.run("daemon", daemon.start, 14)
        completed = device_harness.run("daemon", daemon.isCompleted)
        move_status = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert completed is False
        assert move_status[0] == status.BUSY

    def test_completion_uses_fresh_readback_not_stale_cache(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        fake_backend.emit_update(cfg["readpv"], value=28, units="mm")

        # Act
        device_harness.run("daemon", daemon.start, 14)
        fake_backend.values[cfg["readpv"]] = 14
        completed = device_harness.run("daemon", daemon.isCompleted)

        # Assert
        assert completed is True

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsDigitalMoveable.read(maxage=0)` should bypass monitor "
            "cache and perform a fresh backend read."
        ),
        strict=False,
    )
    def test_digital_moveable_read_maxage_zero_bypasses_cached_value(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 2
        fake_backend.values[cfg["writepv"]] = 2

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.run("poller", daemon._cache.put, daemon._name, "value", 1)

        # Act
        observed = device_harness.run("daemon", daemon.read, 0)

        # Assert
        assert observed == 2

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsDigitalMoveable.status(maxage=0)` should bypass monitor "
            "cache and perform a fresh backend alarm read."
        ),
        strict=False,
    )
    def test_digital_moveable_status_maxage_zero_bypasses_cached_status(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    @pytest.mark.xfail(
        reason=(
            "TDD: stale `targetpv` callbacks should not overwrite the active "
            "daemon command target for `EpicsDigitalMoveable`."
        ),
        strict=False,
    )
    def test_digital_moveable_stale_target_callback_does_not_replace_active_target(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        cfg["targetpv"] = "SIM:M1.TARGET"
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.values[cfg["targetpv"]] = 28
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, 14)
        fake_backend.emit_update(cfg["targetpv"], value=28)
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == 14

    def test_digital_moveable_second_start_wins_when_old_callbacks_arrive_late(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, 28)
        device_harness.run("daemon", daemon.start, 14)
        fake_backend.emit_update(cfg["writepv"], value=28, limits=(-100, 100))
        fake_backend.emit_update(cfg["readpv"], value=28, units="mm")
        observed_target = device_harness.run("daemon", lambda: daemon.target)
        observed_status = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert observed_target == 14
        assert observed_status[0] == status.BUSY
        assert "14" in observed_status[1]

    @pytest.mark.xfail(
        reason=(
            "TDD: without `targetpv`, stale `writepv` callbacks should not "
            "overwrite falsey active targets for `EpicsDigitalMoveable`."
        ),
        strict=False,
    )
    def test_digital_moveable_falsey_target_survives_stale_write_callback_without_targetpv(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, 0)
        fake_backend.emit_update(cfg["writepv"], value=28, limits=(-100, 100))
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == 0

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsDigitalMoveable.read(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_digital_moveable_read_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 3
        fake_backend.values[cfg["writepv"]] = 3

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", 1, time=0.0
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0.1)

        # Assert
        assert observed == 3

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsDigitalMoveable.status(maxage>0)` should reject stale "
            "cache entries and refresh from backend."
        ),
        strict=False,
    )
    def test_digital_moveable_status_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
            time=0.0,
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0.1)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    def test_digital_moveable_maw_raises_moveerror_on_disconnect_during_motion(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )

        # Act
        def _disconnect_during_wait():
            from nicos import session as active_session

            original_delay = active_session.delay
            delay_calls = {"count": 0}

            def controlled_delay(seconds):
                delay_calls["count"] += 1
                if delay_calls["count"] == 1:
                    fake_backend.emit_connection(cfg["readpv"], False)
                if delay_calls["count"] > 20:
                    raise RuntimeError("test guard: maw did not fail on disconnect")
                return original_delay(seconds)

            active_session.delay = controlled_delay
            try:
                with pytest.raises(MoveError):
                    daemon.maw(14)
            finally:
                active_session.delay = original_delay
            return delay_calls["count"]

        delay_calls = device_harness.run("daemon", _disconnect_during_wait)

        # Assert
        assert delay_calls >= 1

    def test_digital_moveable_maw_recovers_from_transient_disconnect_before_next_poll(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )

        # Act
        def _flap_then_recover():
            from nicos import session as active_session

            original_delay = active_session.delay
            delay_calls = {"count": 0}

            def controlled_delay(seconds):
                delay_calls["count"] += 1
                if delay_calls["count"] == 1:
                    fake_backend.emit_connection(cfg["readpv"], False)
                    fake_backend.emit_connection(cfg["readpv"], True)
                    fake_backend.emit_update(cfg["readpv"], value=14, units="mm")
                    fake_backend.emit_update(cfg["writepv"], value=14, limits=(-100, 100))
                if delay_calls["count"] > 20:
                    raise RuntimeError("test guard: maw did not recover")
                return original_delay(seconds)

            active_session.delay = controlled_delay
            try:
                return daemon.maw(14), delay_calls["count"]
            finally:
                active_session.delay = original_delay

        value, delay_calls = device_harness.run("daemon", _flap_then_recover)

        # Assert
        assert delay_calls >= 1
        assert value == 14

    def test_digital_moveable_error_alarm_takes_precedence_and_aborts_completion(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.run("daemon", daemon.start, 14)
        fake_backend.alarms[cfg["readpv"]] = (status.ERROR, "trip")

        # Act + Assert
        assert device_harness.run("daemon", daemon.status, 0)[0] == status.ERROR
        with pytest.raises(MoveError):
            device_harness.run("daemon", daemon.isCompleted)

    @pytest.mark.xfail(
        reason=(
            "TDD: while moving, warning alarms should not cause wait logic to "
            "treat the move as completed."
        ),
        strict=False,
    )
    def test_digital_moveable_warn_alarm_while_moving_does_not_complete_wait(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.run("daemon", daemon.start, 14)
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "limit warning")

        # Act
        observed_status = device_harness.run("daemon", daemon.status, 0)
        completed = device_harness.run("daemon", daemon.isCompleted)

        # Assert
        assert observed_status[0] == status.BUSY
        assert completed is False

    def test_digital_moveable_out_of_order_callbacks_keep_busy_until_readback_arrives(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, 14)
        fake_backend.emit_update(cfg["writepv"], value=14, limits=(-100, 100))
        status_after_write = device_harness.run("daemon", daemon.status, 0)
        fake_backend.emit_update(cfg["readpv"], value=14, units="mm")
        status_after_read = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert status_after_write[0] == status.BUSY
        assert status_after_read[0] == status.OK

    def test_digital_moveable_finish_warns_if_target_not_reached(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        cfg["monitor"] = False
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **cfg,
        )
        device_harness.run("daemon", daemon.start, 14)

        # Act
        def _finish_and_capture_warning():
            messages = []
            original_warning = daemon.log.warning

            def capture_warning(msg, *args, **kwargs):
                del kwargs
                messages.append(msg % args if args else msg)

            daemon.log.warning = capture_warning
            try:
                daemon.finish()
            finally:
                daemon.log.warning = original_warning
            return messages

        warning_messages = device_harness.run("daemon", _finish_and_capture_warning)

        # Assert
        assert any("did not reach target" in msg for msg in warning_messages)


class TestEpicsStringMoveable:
    """Behavior tests for string moveable class."""

    def test_daemon_string_moveable_starts_with_string_target(
        self, device_harness, fake_backend
    ):
        cfg = string_moveable_config()
        cfg["monitor"] = False
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        dev = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.run("daemon", dev.start, "ON")

        assert fake_backend.put_calls[-1] == (cfg["writepv"], "ON", False)
        assert device_harness.run("daemon", dev.status, 0) == (status.OK, "ok")

    def test_daemon_string_moveable_status_returns_timeout_error_on_backend_timeout(
        self, device_harness, fake_backend
    ):
        cfg = string_moveable_config()
        cfg["monitor"] = False
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"
        fake_backend.get_alarm_status = lambda pv: (_ for _ in ()).throw(TimeoutError())

        dev = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        assert device_harness.run("daemon", dev.status, 0) == (
            status.ERROR,
            "timeout reading status",
        )

    def test_poller_string_moveable_value_and_status_callbacks_update_cache(
        self, device_harness, fake_backend
    ):
        cfg = string_moveable_config()
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"

        dev = device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        fake_backend.emit_update(
            cfg["readpv"],
            value="ON",
            units="",
            severity=status.WARN,
            message="limit",
        )
        fake_backend.emit_update(cfg["writepv"], value="ON", units="")

        assert device_harness.run("poller", dev._cache.get, dev, "value") == "ON"
        assert device_harness.run("poller", dev._cache.get, dev, "target") == "ON"
        assert device_harness.run("poller", dev._cache.get, dev, "status") == (
            status.WARN,
            "limit",
        )

    def test_poller_string_moveable_connection_callback_sets_comm_failure(
        self, device_harness, fake_backend
    ):
        cfg = string_moveable_config()
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"

        dev = device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        fake_backend.emit_connection(cfg["readpv"], False)

        assert device_harness.run("poller", dev._cache.get, dev, "status") == (
            status.ERROR,
            "communication failure",
        )

    def test_daemon_string_moveable_prefers_cached_value_and_status_from_poller(
        self, device_harness, fake_backend
    ):
        cfg = string_moveable_config()
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "backend-ok")

        daemon = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )

        fake_backend.emit_update(
            cfg["readpv"],
            value="ON",
            units="",
            severity=status.WARN,
            message="from-callback",
        )
        fake_backend.values[cfg["readpv"]] = "BACKEND-STALE"
        get_calls_before = len(fake_backend.get_calls)

        assert device_harness.run("daemon", daemon.read) == "ON"
        assert device_harness.run("daemon", daemon.status) == (
            status.WARN,
            "from-callback",
        )
        assert len(fake_backend.get_calls) == get_calls_before

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsStringMoveable.read(maxage=0)` should bypass monitor cache "
            "and perform a fresh backend read."
        ),
        strict=False,
    )
    def test_string_moveable_read_maxage_zero_bypasses_cached_value(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = string_moveable_config()
        fake_backend.values[cfg["readpv"]] = "ON"
        fake_backend.values[cfg["writepv"]] = "ON"

        daemon = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", "OFF"
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0)

        # Assert
        assert observed == "ON"

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsStringMoveable.status(maxage=0)` should bypass monitor "
            "cache and perform a fresh backend alarm read."
        ),
        strict=False,
    )
    def test_string_moveable_status_maxage_zero_bypasses_cached_status(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = string_moveable_config()
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    @pytest.mark.xfail(
        reason=(
            "TDD: stale `targetpv` callbacks should not overwrite the active "
            "daemon command target for `EpicsStringMoveable`."
        ),
        strict=False,
    )
    def test_string_moveable_stale_target_callback_does_not_replace_active_target(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = string_moveable_config()
        cfg["targetpv"] = "SIM:SEL.TARGET"
        fake_backend.values[cfg["readpv"]] = "OLD"
        fake_backend.values[cfg["writepv"]] = "OLD"
        fake_backend.values[cfg["targetpv"]] = "OLD"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, "NEW")
        fake_backend.emit_update(cfg["targetpv"], value="OLD")
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == "NEW"

    def test_string_moveable_second_start_wins_when_old_callbacks_arrive_late(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = string_moveable_config()
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, "ON")
        device_harness.run("daemon", daemon.start, "OFF")
        fake_backend.emit_update(cfg["writepv"], value="ON", units="")
        fake_backend.emit_update(cfg["readpv"], value="ON", units="")
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == "OFF"

    @pytest.mark.xfail(
        reason=(
            "TDD: without `targetpv`, stale `writepv` callbacks should not "
            "overwrite falsey active targets for `EpicsStringMoveable`."
        ),
        strict=False,
    )
    def test_string_moveable_falsey_target_survives_stale_write_callback_without_targetpv(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = string_moveable_config()
        fake_backend.values[cfg["readpv"]] = "ON"
        fake_backend.values[cfg["writepv"]] = "ON"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, "")
        fake_backend.emit_update(cfg["writepv"], value="ON", units="")
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == ""

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsStringMoveable.read(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_string_moveable_read_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = string_moveable_config()
        fake_backend.values[cfg["readpv"]] = "NEW"
        fake_backend.values[cfg["writepv"]] = "NEW"

        daemon = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", "OLD", time=0.0
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0.1)

        # Assert
        assert observed == "NEW"

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsStringMoveable.status(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_string_moveable_status_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = string_moveable_config()
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
            time=0.0,
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0.1)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsStringMoveable.maw()` should not complete before fresh "
            "readback reaches the new target."
        ),
        strict=False,
    )
    def test_string_moveable_maw_waits_for_fresh_readback_not_stale_value(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = string_moveable_config()
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )

        # Act
        value = device_harness.run("daemon", daemon.maw, "ON")

        # Assert
        assert value == "ON"

    def test_string_moveable_out_of_order_callbacks_do_not_swap_last_target(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = string_moveable_config()
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        daemon = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, "ON")
        fake_backend.emit_update(cfg["writepv"], value="ON", units="")
        fake_backend.emit_update(cfg["readpv"], value="OFF", units="")
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == "ON"

    def test_string_moveable_finish_warns_if_target_not_reached(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = string_moveable_config()
        cfg["monitor"] = False
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **cfg,
        )
        device_harness.run("daemon", daemon.start, "ON")

        # Act
        def _finish_and_capture_warning():
            messages = []
            original_warning = daemon.log.warning

            def capture_warning(msg, *args, **kwargs):
                del kwargs
                messages.append(msg % args if args else msg)

            daemon.log.warning = capture_warning
            try:
                daemon.finish()
            finally:
                daemon.log.warning = original_warning
            return messages

        warning_messages = device_harness.run("daemon", _finish_and_capture_warning)

        # Assert
        assert any("did not reach target" in msg for msg in warning_messages)


class TestEpicsMappedReadable:
    """Behavior tests for mapped readable class."""

    def test_daemon_mapped_readable_initializes_mapping_from_choices(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:MAP.RBV"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = "ON"

        dev = device_harness.create(
            "daemon",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
            monitor=False,
        )

        assert device_harness.run("daemon", lambda: dev.mapping) == {
            "OFF": 0,
            "ON": 1,
        }
        assert device_harness.run("daemon", dev.read, 0) == "ON"

    def test_poller_mapped_readable_callback_loads_mapping_lazily(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:MAP.RBV"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = 0

        dev = device_harness.create(
            "poller",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        fake_backend.emit_update(readpv, value=1, units="")

        assert device_harness.run("poller", lambda: dev.mapping) == {
            "OFF": 0,
            "ON": 1,
        }
        assert device_harness.run("poller", dev._cache.get, dev, "value") == "ON"

    def test_daemon_mapped_readable_prefers_cached_value_when_monitor_enabled(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:MAP.RBV"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = 0

        daemon = device_harness.create(
            "daemon",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        fake_backend.emit_update(readpv, value=1, units="")
        fake_backend.values[readpv] = 0
        get_calls_before = len(fake_backend.get_calls)

        assert device_harness.run("daemon", daemon.read) == "ON"
        assert len(fake_backend.get_calls) == get_calls_before

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsMappedReadable.read(maxage=0)` should bypass monitor cache "
            "and perform a fresh backend read."
        ),
        strict=False,
    )
    def test_mapped_readable_read_maxage_zero_bypasses_cached_value(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:MAPREAD"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = "ON"

        daemon = device_harness.create(
            "daemon",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", "OFF"
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0)

        # Assert
        assert observed == "ON"

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsMappedReadable.status(maxage=0)` should bypass monitor "
            "cache and perform a fresh backend alarm read."
        ),
        strict=False,
    )
    def test_mapped_readable_status_maxage_zero_bypasses_cached_status(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:MAPREAD:STATUS"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = "OFF"
        fake_backend.alarms[readpv] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    def test_mapped_readable_unknown_callback_value_is_forwarded_as_raw(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAP:UNKNOWN.RBV"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = 0

        dev = device_harness.create(
            "poller",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )

        # Act
        fake_backend.emit_update(readpv, value=99, units="")

        # Assert
        assert device_harness.run("poller", dev._cache.get, dev, "value") == 99

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsMappedReadable.read(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_mapped_readable_read_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:MAPREAD:POSITIVE"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = "ON"

        daemon = device_harness.create(
            "daemon",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", "OFF", time=0.0
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0.1)

        # Assert
        assert observed == "ON"

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsMappedReadable.status(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_mapped_readable_status_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        readpv = "SIM:MAXAGE:MAPREAD:STATUS:POSITIVE"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = "OFF"
        fake_backend.alarms[readpv] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        device_harness.create(
            "poller",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
            time=0.0,
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0.1)

        # Assert
        assert observed == (status.WARN, "fresh alarm")


class TestEpicsMappedMoveable:
    """Behavior tests for mapped moveable class."""

    def test_daemon_mapped_moveable_maps_user_target_to_raw_value(
        self, device_harness, fake_backend
    ):
        cfg = mapped_config()
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0

        dev = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            monitor=False,
        )
        device_harness.run("daemon", dev.start, "ON")

        assert device_harness.run("daemon", lambda: dev.mapping) == {
            "OFF": 0,
            "ON": 1,
        }
        assert fake_backend.put_calls[-1] == (cfg["writepv"], 1, False)

    def test_poller_mapped_moveable_callback_maps_readback_and_target(
        self, device_harness, fake_backend
    ):
        cfg = mapped_config()
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0

        dev = device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        fake_backend.emit_update(cfg["readpv"], value=1, units="")
        fake_backend.emit_update(cfg["writepv"], value=1, units="")

        assert device_harness.run("poller", dev._cache.get, dev, "value") == "ON"
        assert device_harness.run("poller", dev._cache.get, dev, "target") == 1

    def test_daemon_mapped_moveable_prefers_cached_readback_from_poller(
        self, device_harness, fake_backend
    ):
        cfg = mapped_config()
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0

        daemon = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
        )
        fake_backend.emit_update(cfg["readpv"], value=1, units="")
        fake_backend.values[cfg["readpv"]] = 0
        get_calls_before = len(fake_backend.get_calls)

        assert device_harness.run("daemon", daemon.read) == "ON"
        assert len(fake_backend.get_calls) == get_calls_before

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsMappedMoveable.read(maxage=0)` should bypass monitor cache "
            "and perform a fresh backend read."
        ),
        strict=False,
    )
    def test_mapped_moveable_read_maxage_zero_bypasses_cached_value(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = mapped_config()
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = "ON"
        fake_backend.values[cfg["writepv"]] = "ON"

        daemon = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", "OFF"
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0)

        # Assert
        assert observed == "ON"

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsMappedMoveable.status(maxage=0)` should bypass monitor "
            "cache and perform a fresh backend alarm read."
        ),
        strict=False,
    )
    def test_mapped_moveable_status_maxage_zero_bypasses_cached_status(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = mapped_config()
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    @pytest.mark.xfail(
        reason=(
            "TDD: stale `targetpv` callbacks should not overwrite the active "
            "daemon command target for `EpicsMappedMoveable`."
        ),
        strict=False,
    )
    def test_mapped_moveable_stale_target_callback_does_not_replace_active_target(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = mapped_config()
        cfg["targetpv"] = "SIM:MAP.TARGET"
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.values[cfg["targetpv"]] = 0
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            targetpv=cfg["targetpv"],
            mapping=cfg["mapping"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            targetpv=cfg["targetpv"],
            mapping=cfg["mapping"],
        )

        # Act
        device_harness.run("daemon", daemon.start, "ON")
        fake_backend.emit_update(cfg["targetpv"], value=0)
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == "ON"

    def test_mapped_moveable_second_start_wins_when_old_callbacks_arrive_late(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = mapped_config()
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )

        # Act
        device_harness.run("daemon", daemon.start, "ON")
        device_harness.run("daemon", daemon.start, "OFF")
        fake_backend.emit_update(cfg["writepv"], value=1, units="")
        fake_backend.emit_update(cfg["readpv"], value=1, units="")
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == "OFF"

    @pytest.mark.xfail(
        reason=(
            "TDD: without `targetpv`, stale `writepv` callbacks should not "
            "overwrite falsey active targets for `EpicsMappedMoveable`."
        ),
        strict=False,
    )
    def test_mapped_moveable_falsey_target_survives_stale_write_callback_without_targetpv(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = mapped_config()
        cfg["mapping"] = {"": 0, "ON": 1}
        fake_backend.value_choices[cfg["readpv"]] = ["", "ON"]
        fake_backend.values[cfg["readpv"]] = 1
        fake_backend.values[cfg["writepv"]] = 1
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )

        # Act
        device_harness.run("daemon", daemon.start, "")
        fake_backend.emit_update(cfg["writepv"], value=1, units="")
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == ""

    def test_mapped_moveable_unknown_callback_value_is_forwarded_as_raw(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = mapped_config()
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0

        dev = device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )

        # Act
        fake_backend.emit_update(cfg["readpv"], value=99, units="")

        # Assert
        assert device_harness.run("poller", dev._cache.get, dev, "value") == 99

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsMappedMoveable.read(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_mapped_moveable_read_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = mapped_config()
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = "ON"
        fake_backend.values[cfg["writepv"]] = "ON"

        daemon = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", "OFF", time=0.0
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0.1)

        # Assert
        assert observed == "ON"

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsMappedMoveable.status(maxage>0)` should reject stale cache "
            "entries and refresh from backend."
        ),
        strict=False,
    )
    def test_mapped_moveable_status_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = mapped_config()
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = "OFF"
        fake_backend.values[cfg["writepv"]] = "OFF"
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
            time=0.0,
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0.1)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsMappedMoveable.maw()` should not complete before fresh "
            "readback reaches the new target."
        ),
        strict=False,
    )
    def test_mapped_moveable_maw_waits_for_fresh_readback_not_stale_value(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = mapped_config()
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )

        # Act
        value = device_harness.run("daemon", daemon.maw, "ON")

        # Assert
        assert value == "ON"

    def test_mapped_moveable_out_of_order_callbacks_do_not_swap_last_target(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = mapped_config()
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        daemon = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
        )

        # Act
        device_harness.run("daemon", daemon.start, "ON")
        fake_backend.emit_update(cfg["writepv"], value=1, units="")
        fake_backend.emit_update(cfg["readpv"], value=0, units="")
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == "ON"

    def test_mapped_moveable_finish_warns_if_target_not_reached(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = mapped_config()
        cfg["monitor"] = False
        fake_backend.value_choices[cfg["readpv"]] = ["OFF", "ON"]
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=cfg["readpv"],
            writepv=cfg["writepv"],
            mapping=cfg["mapping"],
            monitor=False,
        )
        device_harness.run("daemon", daemon.start, "ON")

        # Act
        def _finish_and_capture_warning():
            messages = []
            original_warning = daemon.log.warning

            def capture_warning(msg, *args, **kwargs):
                del kwargs
                messages.append(msg % args if args else msg)

            daemon.log.warning = capture_warning
            try:
                daemon.finish()
            finally:
                daemon.log.warning = original_warning
            return messages

        warning_messages = device_harness.run("daemon", _finish_and_capture_warning)

        # Assert
        assert any("did not reach target" in msg for msg in warning_messages)


class TestEpicsManualMappedAnalogMoveable:
    """Behavior tests for manual mapped analog moveable class."""

    def test_daemon_manual_mapped_moveable_writes_busy_status_and_raw_target(
        self, device_harness, fake_backend
    ):
        cfg = analog_moveable_config()
        cfg["mapping"] = {"0 Hz": 0, "10 Hz": 10}
        cfg["monitor"] = False
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.units[cfg["readpv"]] = "Hz"
        fake_backend.limits[cfg["writepv"]] = (0, 20)

        dev = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )

        device_harness.run("daemon", dev.start, "10 Hz")

        assert fake_backend.put_calls[-1] == (cfg["writepv"], 10, False)
        assert device_harness.run("daemon", dev._cache.get, dev, "status")[0] == (
            status.BUSY
        )
        assert device_harness.run("daemon", dev.doReadTarget) == "10 Hz"

    def test_poller_manual_mapped_callbacks_update_status_and_limits(
        self, device_harness, fake_backend
    ):
        cfg = analog_moveable_config()
        cfg["mapping"] = {"0 Hz": 0, "10 Hz": 10}
        cfg["targetpv"] = "SIM:MAP.TARGET"
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.values[cfg["targetpv"]] = 0
        fake_backend.units[cfg["readpv"]] = "Hz"
        fake_backend.limits[cfg["writepv"]] = (0, 20)

        dev = device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )

        fake_backend.emit_update(cfg["readpv"], value=3, units="Hz")
        fake_backend.emit_update(cfg["targetpv"], value=10)
        fake_backend.emit_update(cfg["writepv"], value=10, limits=(0, 20))

        assert device_harness.run("poller", dev._cache.get, dev, "value") == 3
        assert device_harness.run("poller", dev._cache.get, dev, "abslimits") == (
            0,
            20,
        )
        assert device_harness.run("poller", dev._cache.get, dev, "status")[0] == (
            status.BUSY
        )

        fake_backend.emit_update(cfg["readpv"], value=10, units="Hz")
        assert device_harness.run("poller", dev._cache.get, dev, "status")[0] == (
            status.OK
        )

    def test_daemon_manual_mapped_reads_poller_status_transitions(
        self, device_harness, fake_backend
    ):
        cfg = analog_moveable_config()
        cfg["mapping"] = {"0 Hz": 0, "10 Hz": 10}
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.units[cfg["readpv"]] = "Hz"

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )

        device_harness.run("daemon", daemon.start, "10 Hz")
        assert device_harness.run("daemon", daemon.status, 0)[0] == status.BUSY

        fake_backend.emit_update(cfg["readpv"], value=10, units="Hz")
        fake_backend.emit_update(cfg["writepv"], value=10, limits=(0, 20))
        assert device_harness.run("daemon", daemon.status, 0)[0] == status.OK

        fake_backend.emit_update(cfg["readpv"], value=5, units="Hz")
        assert device_harness.run("daemon", daemon.status, 0)[0] == status.BUSY

    def test_daemon_manual_mapped_read_prefers_cached_value_when_monitor_enabled(
        self, device_harness, fake_backend
    ):
        cfg = analog_moveable_config()
        cfg["mapping"] = {"0 Hz": 0, "10 Hz": 10}
        fake_backend.values[cfg["readpv"]] = 0
        fake_backend.values[cfg["writepv"]] = 0
        fake_backend.units[cfg["readpv"]] = "Hz"

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )

        fake_backend.emit_update(cfg["readpv"], value=10, units="Hz")
        fake_backend.values[cfg["readpv"]] = 0
        get_calls_before = len(fake_backend.get_calls)

        assert device_harness.run("daemon", daemon.read) == 10
        assert len(fake_backend.get_calls) == get_calls_before

    @pytest.mark.xfail(
        reason=(
            "TDD: manual-mapped completion currently consults stale monitor "
            "cache; it should use fresh readback semantics during wait/isCompleted."
        ),
        strict=False,
    )
    def test_completion_uses_fresh_readback_not_stale_cache(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.units[cfg["readpv"]] = "mm"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="moveable",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="moveable",
            **cfg,
        )

        # Stale callback from previous target/value.
        fake_backend.emit_update(cfg["readpv"], value=28, units="mm")

        # Act
        device_harness.run("daemon", daemon.start, "14 Hz")
        fake_backend.values[cfg["readpv"]] = 14  # no callback yet
        completed = device_harness.run("daemon", daemon.isCompleted)

        # Assert: completion should be based on fresh readback, not stale cache.
        assert completed is True

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsManualMappedAnalogMoveable.read(maxage=0)` should bypass "
            "monitor cache and perform a fresh backend read."
        ),
        strict=False,
    )
    def test_manual_mapped_read_maxage_zero_bypasses_cached_value(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.run("poller", daemon._cache.put, daemon._name, "value", 14)

        # Act
        observed = device_harness.run("daemon", daemon.read, 0)

        # Assert
        assert observed == 28

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsManualMappedAnalogMoveable.status(maxage=0)` should bypass "
            "monitor cache and perform a fresh backend alarm/status read."
        ),
        strict=False,
    )
    def test_manual_mapped_status_maxage_zero_bypasses_cached_status(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        fake_backend.values[cfg["readpv"]] = 14
        fake_backend.values[cfg["writepv"]] = 14
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    @pytest.mark.xfail(
        reason=(
            "TDD: stale `targetpv` callbacks should not overwrite the active "
            "daemon command target for `EpicsManualMappedAnalogMoveable`."
        ),
        strict=False,
    )
    def test_manual_mapped_stale_target_callback_does_not_replace_active_target(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        cfg["targetpv"] = "SIM:MAP.TARGET"
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.values[cfg["targetpv"]] = 28
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, "14 Hz")
        fake_backend.emit_update(cfg["targetpv"], value=28)
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == "14 Hz"

    @pytest.mark.xfail(
        reason=(
            "TDD: stale callbacks from a previous command should not make "
            "manual-mapped status appear complete for a newer target."
        ),
        strict=False,
    )
    def test_manual_mapped_second_start_wins_when_old_callbacks_arrive_late(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        cfg["mapping"] = {"14 Hz": 14, "28 Hz": 28}
        fake_backend.values[cfg["readpv"]] = 14
        fake_backend.values[cfg["writepv"]] = 14
        fake_backend.units[cfg["readpv"]] = "Hz"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, "28 Hz")
        device_harness.run("daemon", daemon.start, "14 Hz")
        fake_backend.emit_update(cfg["writepv"], value=28, limits=(0, 40))
        fake_backend.emit_update(cfg["readpv"], value=28, units="Hz")
        observed_target = device_harness.run("daemon", lambda: daemon.target)
        observed_status = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert observed_target == "14 Hz"
        assert observed_status[0] == status.BUSY
        assert "14" in observed_status[1]

    @pytest.mark.xfail(
        reason=(
            "TDD: without `targetpv`, stale `writepv` callbacks should not "
            "overwrite falsey active targets for manual mapped moveables."
        ),
        strict=False,
    )
    def test_manual_mapped_falsey_target_survives_stale_write_callback_without_targetpv(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        cfg["mapping"] = {0: 0, 10: 10}
        fake_backend.values[cfg["readpv"]] = 10
        fake_backend.values[cfg["writepv"]] = 10
        fake_backend.units[cfg["readpv"]] = "Hz"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, 0)
        fake_backend.emit_update(cfg["writepv"], value=10, limits=(0, 40))
        observed_target = device_harness.run("daemon", lambda: daemon.target)

        # Assert
        assert observed_target == 0

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsManualMappedAnalogMoveable.read(maxage>0)` should reject "
            "stale cache entries and refresh from backend."
        ),
        strict=False,
    )
    def test_manual_mapped_read_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.run(
            "poller", daemon._cache.put, daemon._name, "value", 14, time=0.0
        )

        # Act
        observed = device_harness.run("daemon", daemon.read, 0.1)

        # Assert
        assert observed == 28

    @pytest.mark.xfail(
        reason=(
            "TDD: `EpicsManualMappedAnalogMoveable.status(maxage>0)` should reject "
            "stale cache entries and refresh from backend."
        ),
        strict=False,
    )
    def test_manual_mapped_status_positive_maxage_rejects_stale_timestamp(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        fake_backend.values[cfg["readpv"]] = 14
        fake_backend.values[cfg["writepv"]] = 14
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "fresh alarm")

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.run(
            "poller",
            daemon._cache.put,
            daemon._name,
            "status",
            (status.OK, "stale alarm"),
            time=0.0,
        )

        # Act
        observed = device_harness.run("daemon", daemon.status, 0.1)

        # Assert
        assert observed == (status.WARN, "fresh alarm")

    @pytest.mark.xfail(
        reason=(
            "TDD: disconnect during manual-mapped wait should abort with "
            "MoveError instead of hanging."
        ),
        strict=False,
    )
    def test_manual_mapped_maw_raises_moveerror_on_disconnect_during_motion(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.units[cfg["readpv"]] = "Hz"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )

        # Act
        def _disconnect_during_wait():
            from nicos import session as active_session

            original_delay = active_session.delay
            delay_calls = {"count": 0}

            def controlled_delay(seconds):
                delay_calls["count"] += 1
                if delay_calls["count"] == 1:
                    fake_backend.emit_connection(cfg["readpv"], False)
                if delay_calls["count"] > 20:
                    raise RuntimeError("test guard: maw did not fail on disconnect")
                return original_delay(seconds)

            active_session.delay = controlled_delay
            try:
                with pytest.raises(MoveError):
                    daemon.maw("14 Hz")
            finally:
                active_session.delay = original_delay
            return delay_calls["count"]

        delay_calls = device_harness.run("daemon", _disconnect_during_wait)

        # Assert
        assert delay_calls >= 1

    def test_manual_mapped_maw_recovers_from_transient_disconnect_before_next_poll(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.units[cfg["readpv"]] = "Hz"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )

        # Act
        def _flap_then_recover():
            from nicos import session as active_session

            original_delay = active_session.delay
            delay_calls = {"count": 0}

            def controlled_delay(seconds):
                delay_calls["count"] += 1
                if delay_calls["count"] == 1:
                    fake_backend.emit_connection(cfg["readpv"], False)
                    fake_backend.emit_connection(cfg["readpv"], True)
                    fake_backend.emit_update(cfg["readpv"], value=14, units="Hz")
                    fake_backend.emit_update(cfg["writepv"], value=14, limits=(0, 40))
                if delay_calls["count"] > 20:
                    raise RuntimeError("test guard: maw did not recover")
                return original_delay(seconds)

            active_session.delay = controlled_delay
            try:
                return daemon.maw("14 Hz"), delay_calls["count"]
            finally:
                active_session.delay = original_delay

        value, delay_calls = device_harness.run("daemon", _flap_then_recover)

        # Assert
        assert delay_calls >= 1
        assert value == 14

    @pytest.mark.xfail(
        reason=(
            "TDD: manual-mapped completion should treat ERROR alarm state as "
            "terminal wait failure, not success."
        ),
        strict=False,
    )
    def test_manual_mapped_error_alarm_aborts_completion(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.run("daemon", daemon.start, "14 Hz")
        fake_backend.alarms[cfg["readpv"]] = (status.ERROR, "trip")

        # Act + Assert
        with pytest.raises(MoveError):
            device_harness.run("daemon", daemon.isCompleted)

    def test_manual_mapped_warn_alarm_while_moving_does_not_complete_wait(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.run("daemon", daemon.start, "14 Hz")
        fake_backend.alarms[cfg["readpv"]] = (status.WARN, "limit warning")

        # Act
        observed_status = device_harness.run("daemon", daemon.status, 0)
        completed = device_harness.run("daemon", daemon.isCompleted)

        # Assert
        assert observed_status[0] == status.BUSY
        assert completed is False

    def test_manual_mapped_out_of_order_callbacks_keep_busy_until_readback_arrives(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.units[cfg["readpv"]] = "Hz"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")
        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )

        # Act
        device_harness.run("daemon", daemon.start, "14 Hz")
        fake_backend.emit_update(cfg["writepv"], value=14, limits=(0, 40))
        status_after_write = device_harness.run("daemon", daemon.status, 0)
        fake_backend.emit_update(cfg["readpv"], value=14, units="Hz")
        status_after_read = device_harness.run("daemon", daemon.status, 0)

        # Assert
        assert status_after_write[0] == status.BUSY
        assert status_after_read[0] == status.OK

    def test_manual_mapped_finish_warns_if_target_not_reached(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = _manual_moveable_config()
        cfg["monitor"] = False
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        device_harness.run("daemon", daemon.start, "14 Hz")

        # Act
        def _finish_and_capture_warning():
            messages = []
            original_warning = daemon.log.warning

            def capture_warning(msg, *args, **kwargs):
                del kwargs
                messages.append(msg % args if args else msg)

            daemon.log.warning = capture_warning
            try:
                daemon.finish()
            finally:
                daemon.log.warning = original_warning
            return messages

        warning_messages = device_harness.run("daemon", _finish_and_capture_warning)

        # Assert
        assert any("did not reach target" in msg for msg in warning_messages)

    def test_manual_mapped_status_message_uses_current_target_not_previous_one(
        self, device_harness, fake_backend
    ):
        # Setup
        cfg = analog_moveable_config()
        cfg["mapping"] = {"14 Hz": 14, "28 Hz": 28}
        fake_backend.values[cfg["readpv"]] = 28
        fake_backend.values[cfg["writepv"]] = 28
        fake_backend.units[cfg["readpv"]] = "Hz"
        fake_backend.alarms[cfg["readpv"]] = (status.OK, "ok")

        daemon = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )
        poller = device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **cfg,
        )

        # Simulate poller still holding previous command target.
        device_harness.run("poller", poller._setROParam, "target", "28 Hz")

        # Act
        device_harness.run("daemon", daemon.start, "14 Hz")
        fake_backend.emit_update(cfg["readpv"], value=28, units="Hz")
        st = device_harness.run("daemon", daemon.status)

        # Assert
        assert st[0] == status.BUSY
        assert "14" in st[1]
