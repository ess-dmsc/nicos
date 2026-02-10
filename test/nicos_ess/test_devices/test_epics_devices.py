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
# *****************************************************************************

import time
import unittest

import numpy
import pytest

from nicos.core import MAIN, POLLER, status
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsAnalogMoveable,
    EpicsManualMappedAnalogMoveable,
    EpicsMappedMoveable,
    EpicsMappedReadable,
    EpicsReadable,
    EpicsStringReadable,
    get_from_cache_or,
)


session_setup = None


class FakeSubscription:
    def __init__(self, pvname, pvparam, callback, connection_callback):
        self.pvname = pvname
        self.pvparam = pvparam
        self.callback = callback
        self.connection_callback = connection_callback
        self.closed = False

    def close(self):
        self.closed = True


class FakeEpicsWrapper:
    def __init__(self):
        self.values = {}
        self.units = {}
        self.alarms = {}
        self.limits = {}
        self.choices = {}
        self.connect_calls = []
        self.get_value_calls = []
        self.put_calls = []
        self.subscribe_calls = []
        self.closed_subscriptions = []
        self.raise_timeout_on_alarm = False
        self._subscriptions = []

    def connect_pv(self, pvname):
        self.connect_calls.append(pvname)

    def get_pv_value(self, pvname, as_string=False):
        self.get_value_calls.append((pvname, as_string))
        value = self.values[pvname]
        if as_string and isinstance(value, numpy.ndarray):
            return "".join(chr(x) for x in value)
        return value

    def put_pv_value(self, pvname, value, wait=False):
        self.put_calls.append((pvname, value, wait))
        self.values[pvname] = value

    def get_alarm_status(self, pvname):
        if self.raise_timeout_on_alarm:
            raise TimeoutError("timeout")
        return self.alarms.get(pvname, (status.OK, ""))

    def get_units(self, pvname):
        return self.units.get(pvname, "")

    def get_limits(self, pvname):
        return self.limits.get(pvname, (-1e308, 1e308))

    def get_value_choices(self, pvname):
        return self.choices.get(pvname, [])

    def subscribe(
        self,
        pvname,
        pvparam,
        change_callback,
        connection_callback=None,
        as_string=False,
    ):
        sub = FakeSubscription(pvname, pvparam, change_callback, connection_callback)
        self.subscribe_calls.append((pvname, pvparam, as_string))
        self._subscriptions.append(sub)
        return sub

    def close_subscription(self, sub):
        self.closed_subscriptions.append(sub)
        sub.close()

    def emit_change(
        self,
        pvname,
        pvparam,
        value,
        units="",
        limits=None,
        severity=status.OK,
        message="",
    ):
        for sub in self._subscriptions:
            if sub.closed:
                continue
            if sub.pvname == pvname and sub.pvparam == pvparam and sub.callback:
                sub.callback(
                    pvname, pvparam, value, units, limits, severity, message
                )

    def emit_connection(self, pvname, pvparam, is_connected, **kwargs):
        for sub in self._subscriptions:
            if sub.closed:
                continue
            if (
                sub.pvname == pvname
                and sub.pvparam == pvparam
                and sub.connection_callback
            ):
                sub.connection_callback(pvname, pvparam, is_connected, **kwargs)


def _base_wrapper():
    wrapper = FakeEpicsWrapper()
    wrapper.values.update(
        {
            "TEST:READ": 12.5,
            "TEST:STR:READ": "hello",
            "TEST:ANA:READ": 1.5,
            "TEST:ANA:WRITE": 1.5,
            "TEST:ANAT:READ": 2.5,
            "TEST:ANAT:WRITE": 2.5,
            "TEST:ANAT:TARGET": 2.5,
            "TEST:MAP:READ": 1,
            "TEST:MMAP:READ": "OPEN",
            "TEST:MMAP:WRITE": 1,
            "TEST:MAN:READ": 10.0,
            "TEST:MAN:WRITE": 10.0,
            "TEST:MAN:TARGET": 10.0,
        }
    )
    wrapper.units.update(
        {
            "TEST:READ": "K",
            "TEST:ANA:READ": "mm",
            "TEST:ANAT:READ": "deg",
            "TEST:MAN:READ": "rpm",
        }
    )
    wrapper.alarms.update(
        {
            "TEST:READ": (status.OK, ""),
            "TEST:ANA:READ": (status.OK, ""),
            "TEST:ANAT:READ": (status.OK, ""),
            "TEST:MMAP:READ": (status.OK, ""),
            "TEST:MAN:READ": (status.OK, ""),
        }
    )
    wrapper.limits.update(
        {
            "TEST:ANA:WRITE": (-5.0, 5.0),
            "TEST:ANAT:WRITE": (-10.0, 10.0),
            "TEST:MAN:WRITE": (0.0, 30.0),
        }
    )
    wrapper.choices.update(
        {
            "TEST:MAP:READ": ["OFF", "ON"],
            "TEST:MMAP:READ": ["CLOSED", "OPEN"],
        }
    )
    return wrapper


class _FakeWrapperMixin:
    class _LocalCache:
        def __init__(self):
            self._store = {}
            self._callbacks = {}

        def get(self, *args):
            if len(args) == 2:
                name, key = args
                default = None
            elif len(args) == 3:
                name, key, default = args
            else:
                raise TypeError(f"unexpected get() args count: {len(args)}")
            return self._store.get((name, key), default)

        def put(self, *args):
            if len(args) >= 3:
                name, key, value = args[:3]
            else:
                raise TypeError(f"unexpected put() args: {args!r}")
            self._store[(name, key)] = value

        def addCallback(self, name, key, callback):
            self._callbacks.setdefault((name, key), []).append(callback)

        def removeCallback(self, name, key, callback):
            callbacks = self._callbacks.get((name, key), [])
            if callback in callbacks:
                callbacks.remove(callback)

    def _ensure_local_cache(self):
        if getattr(self, "_cache", None) is None:
            self._cache = self._LocalCache()

    def _new_wrapper(self):
        return _base_wrapper()


class FakeEpicsReadableDevice(_FakeWrapperMixin, EpicsReadable):
    def doPreinit(self, mode):
        self._ensure_local_cache()
        self._epics_subscriptions = []
        self._epics_wrapper = self._new_wrapper()
        self._epics_wrapper.connect_pv(self.readpv)


class FakeEpicsStringReadableDevice(_FakeWrapperMixin, EpicsStringReadable):
    def doPreinit(self, mode):
        self._ensure_local_cache()
        self._epics_subscriptions = []
        self._epics_wrapper = self._new_wrapper()
        self._epics_wrapper.connect_pv(self.readpv)


class FakeEpicsAnalogMoveableDevice(_FakeWrapperMixin, EpicsAnalogMoveable):
    def doPreinit(self, mode):
        self._ensure_local_cache()
        self._epics_subscriptions = []
        self._epics_wrapper = self._new_wrapper()
        self._epics_wrapper.connect_pv(self.readpv)
        self._epics_wrapper.connect_pv(self.writepv)


class FakeEpicsAnalogMoveableWithTargetDevice(_FakeWrapperMixin, EpicsAnalogMoveable):
    def doPreinit(self, mode):
        self._ensure_local_cache()
        self._epics_subscriptions = []
        self._epics_wrapper = self._new_wrapper()
        self._epics_wrapper.connect_pv(self.readpv)
        self._epics_wrapper.connect_pv(self.writepv)
        self._epics_wrapper.connect_pv(self.targetpv)


class FakeEpicsMappedReadableDevice(_FakeWrapperMixin, EpicsMappedReadable):
    def doPreinit(self, mode):
        self._ensure_local_cache()
        self._epics_subscriptions = []
        self._epics_wrapper = self._new_wrapper()
        self._epics_wrapper.connect_pv(self.readpv)


class FakeEpicsMappedMoveableDevice(_FakeWrapperMixin, EpicsMappedMoveable):
    def doPreinit(self, mode):
        self._ensure_local_cache()
        self._epics_subscriptions = []
        self._epics_wrapper = self._new_wrapper()
        self._epics_wrapper.connect_pv(self.readpv)
        self._epics_wrapper.connect_pv(self.writepv)


class FakeEpicsManualMappedAnalogMoveableDevice(
    _FakeWrapperMixin, EpicsManualMappedAnalogMoveable
):
    def doPreinit(self, mode):
        self._ensure_local_cache()
        self._epics_subscriptions = []
        self._epics_wrapper = self._new_wrapper()
        self._epics_wrapper.connect_pv(self.readpv)
        self._epics_wrapper.connect_pv(self.writepv)
        self._epics_wrapper.connect_pv(self.targetpv)


class TestEpicsPvaReadable(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.session.sessiontype = POLLER
        self.session.unloadSetup()
        self.session.loadSetup("ess_epics_devices", {})
        self.device = self.session.getDevice("PvaReadable")
        yield
        self.session.unloadSetup()
        self.session.sessiontype = MAIN

    def test_connect_and_subscribe_on_init(self):
        wrapper = self.device._epics_wrapper
        assert wrapper.connect_calls == ["TEST:READ"]
        assert len(wrapper.subscribe_calls) == 2
        assert wrapper.subscribe_calls[0] == ("TEST:READ", "value", False)

    def test_read_unit_and_status_paths(self):
        wrapper = self.device._epics_wrapper
        wrapper.alarms["TEST:READ"] = (status.WARN, "alarm")

        assert self.device.doRead() == 12.5
        assert self.device.doReadUnit() == "K"
        assert self.device.doStatus() == (status.WARN, "alarm")

        wrapper.raise_timeout_on_alarm = True
        self.device._setROParam("monitor", False)
        assert self.device.doStatus() == (status.ERROR, "timeout reading status")

    def test_connection_callback_stores_communication_failure(self):
        self.device._connection_change_callback("TEST:READ", "value", False)
        assert self.device._cache.get(self.device._name, "status") == (
            status.ERROR,
            "communication failure",
        )

        self.device._cache.put(self.device._name, "status", None, time.time())
        self.device._connection_change_callback("TEST:READ", "target", False)
        assert self.device._cache.get(self.device._name, "status") is None

    def test_monitor_value_and_status_callbacks_update_cache(self):
        wrapper = self.device._epics_wrapper

        wrapper.emit_change(
            "TEST:READ", "value", 18.5, units="m", limits=None, severity=status.WARN, message="warn"
        )
        assert self.device._cache.get(self.device._name, "value") == 18.5
        assert self.device._cache.get(self.device._name, "unit") == "m"
        assert self.device._cache.get(self.device._name, "status") == (status.WARN, "warn")

    def test_monitor_disconnect_reconnect_and_status_recovery(self):
        wrapper = self.device._epics_wrapper
        wrapper.emit_connection("TEST:READ", "value", False, reason="Disconnected")
        assert self.device._cache.get(self.device._name, "status") == (
            status.ERROR,
            "communication failure",
        )

        wrapper.emit_connection("TEST:READ", "value", True)
        wrapper.emit_change(
            "TEST:READ", "value", 1.0, units="K", limits=None, severity=status.OK, message=""
        )
        assert self.device._cache.get(self.device._name, "status") == (status.OK, "")


class TestEpicsPvaStringReadable(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.session.sessiontype = POLLER
        self.session.unloadSetup()
        self.session.loadSetup("ess_epics_devices", {})
        self.device = self.session.getDevice("PvaStringReadable")
        yield
        self.session.unloadSetup()
        self.session.sessiontype = MAIN

    def test_value_callback_converts_char_waveform_ndarray(self):
        value = numpy.array([65, 66, 67], dtype=numpy.uint8)
        self.device._value_change_callback(
            "TEST:STR:READ", "value", value, "", None, status.OK, ""
        )
        assert self.device._cache.get(self.device._name, "value") == "ABC"

    def test_read_uses_as_string_path(self):
        wrapper = self.device._epics_wrapper
        wrapper.values["TEST:STR:READ"] = numpy.array([88, 89], dtype=numpy.uint8)
        assert self.device.doRead() == "XY"
        assert wrapper.get_value_calls[-1] == ("TEST:STR:READ", True)


class TestEpicsPvaAnalogMoveable(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.session.sessiontype = POLLER
        self.session.unloadSetup()
        self.session.loadSetup("ess_epics_devices", {})
        self.device = self.session.getDevice("PvaAnalogMoveable")
        self.target_device = self.session.getDevice("PvaAnalogMoveableWithTarget")
        yield
        self.session.unloadSetup()
        self.session.sessiontype = MAIN

    def test_do_read_abslimits_uses_defaults_when_zero_limits(self):
        wrapper = self.device._epics_wrapper
        wrapper.limits[self.device.writepv] = (0.0, 0.0)
        assert self.device.doReadAbslimits() == (-1e308, 1e308)

    def test_do_status_busy_when_not_at_target_and_ok_when_aligned(self):
        wrapper = self.device._epics_wrapper
        wrapper.values[self.device.readpv] = 1.0
        wrapper.values[self.device.writepv] = 5.0
        self.device._setROParam("target", 5.0)
        assert self.device._do_status()[0] == status.BUSY

        wrapper.values[self.device.writepv] = 1.0
        self.device._setROParam("target", 1.0)
        assert self.device._do_status() == (status.OK, "")

    def test_do_start_and_value_callback_cache_updates(self):
        wrapper = self.device._epics_wrapper
        self.device.doStart(3.2)
        assert wrapper.put_calls[-1] == ("TEST:ANA:WRITE", 3.2, False)

        self.device._setROParam("target", None)
        self.device._value_change_callback(
            "TEST:ANA:WRITE",
            "target",
            4.2,
            "",
            (-2.0, 6.0),
            status.OK,
            "",
        )
        assert self.device._cache.get(self.device._name, "target") == 4.2
        assert self.device._cache.get(self.device._name, "abslimits") == (-2.0, 6.0)

    def test_do_read_target_uses_targetpv_when_configured(self):
        wrapper = self.target_device._epics_wrapper
        wrapper.values[self.target_device.targetpv] = 7.7
        assert self.target_device.doReadTarget() == 7.7

    def test_do_read_target_uses_writepv_when_no_targetpv(self):
        wrapper = self.device._epics_wrapper
        wrapper.values[self.device.writepv] = 9.9
        assert self.device.doReadTarget() == 9.9

    def test_status_prefers_alarm_over_busy(self):
        wrapper = self.device._epics_wrapper
        wrapper.values[self.device.readpv] = 1.0
        wrapper.values[self.device.writepv] = 5.0
        self.device._setROParam("target", 5.0)
        wrapper.alarms[self.device.readpv] = (status.ERROR, "alarm fail")
        assert self.device._do_status() == (status.ERROR, "alarm fail")

    def test_monitor_callbacks_handle_disconnect_reconnect(self):
        wrapper = self.device._epics_wrapper
        wrapper.emit_connection(self.device.readpv, "value", False)
        assert self.device._cache.get(self.device._name, "status") == (
            status.ERROR,
            "communication failure",
        )
        wrapper.emit_connection(self.device.readpv, "value", True)
        wrapper.emit_change(
            self.device.readpv,
            "value",
            2.2,
            units="mm",
            limits=None,
            severity=status.OK,
            message="",
        )
        assert self.device._cache.get(self.device._name, "value") == 2.2
        assert self.device._cache.get(self.device._name, "unit") == "mm"

    def test_monitor_writepv_and_targetpv_callbacks_update_expected_cache(self):
        wrapper = self.target_device._epics_wrapper
        self.target_device._setROParam("target", None)
        wrapper.emit_change(
            self.target_device.writepv,
            "target",
            5.5,
            units="",
            limits=(-3.0, 7.0),
            severity=status.OK,
            message="",
        )
        assert self.target_device._cache.get(self.target_device._name, "abslimits") == (
            -3.0,
            7.0,
        )
        # Current behavior: writepv update seeds "target" cache when target is not set.
        assert self.target_device._cache.get(self.target_device._name, "target") == 5.5

        wrapper.emit_change(
            self.target_device.targetpv,
            "target",
            6.6,
            units="",
            limits=None,
            severity=status.OK,
            message="",
        )
        assert self.target_device._cache.get(self.target_device._name, "target") == 6.6

    @pytest.mark.xfail(
        reason=(
            "With explicit targetpv configured, target cache ideally should come only "
            "from targetpv monitor updates (not writepv)."
        )
    )
    def test_target_with_targetpv_should_not_be_seeded_from_writepv(self):
        wrapper = self.target_device._epics_wrapper
        self.target_device._setROParam("target", None)
        wrapper.emit_change(
            self.target_device.writepv,
            "target",
            5.5,
            units="",
            limits=(-3.0, 7.0),
            severity=status.OK,
            message="",
        )
        assert self.target_device._cache.get(self.target_device._name, "target") is None


class TestMappedDevices(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.session.sessiontype = POLLER
        self.session.unloadSetup()
        self.session.loadSetup("ess_epics_devices", {})
        self.mapped_readable = self.session.getDevice("PvaMappedReadable")
        self.mapped_moveable = self.session.getDevice("PvaMappedMoveable")
        self.manual_mapped = self.session.getDevice("PvaManualMappedAnalogMoveable")
        yield
        self.session.unloadSetup()
        self.session.sessiontype = MAIN

    def test_mapped_readable_updates_mapping_from_epics_choices(self):
        self.mapped_readable._setROParam("mapping", {})
        self.mapped_readable._inverse_mapping = {}
        self.mapped_readable._value_change_callback(
            "TEST:MAP:READ", "value", 1, "", None, status.OK, ""
        )
        assert self.mapped_readable.mapping == {"OFF": 0, "ON": 1}
        assert self.mapped_readable._cache.get(self.mapped_readable._name, "value") == "ON"

    def test_mapped_moveable_do_start_uses_mapping_raw_value(self):
        wrapper = self.mapped_moveable._epics_wrapper
        self.mapped_moveable.doStart("OPEN")
        assert wrapper.put_calls[-1] == ("TEST:MMAP:WRITE", 1, False)

    def test_mapped_readable_unknown_raw_value_falls_back_to_raw_value(self):
        self.mapped_readable._setROParam("mapping", {"OFF": 0, "ON": 1})
        self.mapped_readable._inverse_mapping = {0: "OFF", 1: "ON"}
        self.mapped_readable._value_change_callback(
            "TEST:MAP:READ", "value", 9, "", None, status.OK, ""
        )
        assert self.mapped_readable._cache.get(self.mapped_readable._name, "value") == 9

    def test_manual_mapped_moveable_status_target_and_is_at_target(self):
        wrapper = self.manual_mapped._epics_wrapper
        self.manual_mapped.doStart("fast")
        assert wrapper.put_calls[-1] == ("TEST:MAN:WRITE", 20.0, False)
        assert self.manual_mapped._cache.get(self.manual_mapped._name, "status")[0] == status.BUSY

        wrapper.values[self.manual_mapped.targetpv] = 10.0
        assert self.manual_mapped.doReadTarget() == "slow"

        wrapper.values[self.manual_mapped.readpv] = 20.0
        self.manual_mapped._setROParam("target", "fast")
        assert self.manual_mapped.doIsAtTarget() is True

    def test_manual_mapped_status_timeout_and_alarm_precedence(self):
        wrapper = self.manual_mapped._epics_wrapper
        wrapper.raise_timeout_on_alarm = True
        assert self.manual_mapped._do_status() == (status.ERROR, "timeout reading status")

        wrapper.raise_timeout_on_alarm = False
        wrapper.alarms[self.manual_mapped.readpv] = (status.WARN, "warn")
        assert self.manual_mapped._do_status() == (status.WARN, "warn")

    def test_manual_mapped_do_read_target_returns_none_for_unknown_raw(self):
        wrapper = self.manual_mapped._epics_wrapper
        wrapper.values[self.manual_mapped.targetpv] = 999.0
        assert self.manual_mapped.doReadTarget() is None


@pytest.mark.xfail(
    reason=(
        "Mapped readable currently updates choices only once (when mapping is empty). "
        "Dynamic choice changes after initial mapping are not refreshed."
    )
)
def test_mapped_readable_dynamic_choice_change_updates_mapping():
    class _Dummy:
        pass

    # Reuse real class behavior through configured test device would be ideal,
    # but this xfail codifies desired runtime behavior.
    # Test intentionally left as TDD marker.
    assert False


def test_get_from_cache_or_prefers_cache_when_monitor_enabled():
    class _Cache:
        def __init__(self):
            self.v = "cached"

        def get(self, _name, _key):
            return self.v

    class _Device:
        monitor = True
        _name = "D"
        _cache = _Cache()

    calls = {"n": 0}

    def _fallback():
        calls["n"] += 1
        return "fallback"

    assert get_from_cache_or(_Device(), "value", _fallback) == "cached"
    assert calls["n"] == 0


def test_get_from_cache_or_calls_fallback_when_monitor_disabled():
    class _Cache:
        def get(self, _name, _key):
            return "cached"

    class _Device:
        monitor = False
        _name = "D"
        _cache = _Cache()

    calls = {"n": 0}

    def _fallback():
        calls["n"] += 1
        return "fallback"

    assert get_from_cache_or(_Device(), "value", _fallback) == "fallback"
    assert calls["n"] == 1
