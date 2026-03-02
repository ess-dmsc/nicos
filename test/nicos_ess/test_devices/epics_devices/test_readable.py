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

"""Harness tests for EpicsReadable and EpicsStringReadable."""

import numpy
import pytest

from nicos.core import status

from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsReadable,
    EpicsStringReadable,
)

from .conftest import assert_error_status


class TestEpicsReadable:
    """Behavior tests for `EpicsReadable` in daemon/poller/shared-cache roles."""

    def test_daemon_readable_uses_direct_epics_reads_when_monitor_disabled(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 1.23
        fake_backend.units[readpv] = "A"
        fake_backend.alarms[readpv] = (status.WARN, "minor alarm")

        device = device_harness.create(
            "daemon",
            EpicsReadable,
            name="readable",
            readpv=readpv,
            monitor=False,
        )

        assert fake_backend.connect_calls == [readpv]
        assert fake_backend.subscriptions == []
        assert device_harness.run("daemon", device.read, 0) == 1.23
        assert device_harness.run("daemon", lambda: device.unit) == "A"
        assert device_harness.run("daemon", device.status, 0) == (
            status.WARN,
            "minor alarm",
        )

    def test_daemon_readable_status_returns_timeout_error_on_backend_timeout(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 1.0
        fake_backend.get_alarm_status = lambda pv: (_ for _ in ()).throw(TimeoutError())

        device = device_harness.create(
            "daemon",
            EpicsReadable,
            name="readable",
            readpv=readpv,
            monitor=False,
        )

        assert device_harness.run("daemon", device.status, 0) == (
            status.ERROR,
            "timeout reading status",
        )

    def test_poller_readable_value_and_status_callbacks_write_cache(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 0.0

        device = device_harness.create(
            "poller",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )

        fake_backend.emit_update(
            readpv,
            value=5.5,
            units="V",
            severity=status.ERROR,
            message="trip",
        )

        assert len(fake_backend.subscriptions) == 2
        assert device_harness.run("poller", device._cache.get, device, "value") == pytest.approx(
            5.5
        )
        assert device_harness.run("poller", device._cache.get, device, "unit") == "V"
        assert device_harness.run("poller", device._cache.get, device, "status") == (
            status.ERROR,
            "trip",
        )

    def test_poller_readable_connection_callback_sets_comm_failure(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 0.0

        device = device_harness.create(
            "poller",
            EpicsReadable,
            name="readable",
            readpv=readpv,
        )

        fake_backend.emit_update(
            readpv,
            value=5.5,
            units="V",
            severity=status.ERROR,
            message="trip",
        )
        fake_backend.emit_connection(readpv, False)

        assert len(fake_backend.subscriptions) == 2
        assert_error_status(
            device_harness.run("poller", device._cache.get, device, "status")
        )

    def test_daemon_readable_can_consume_poller_cached_values(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:READ.RBV"
        fake_backend.values[readpv] = 0.0

        daemon_device = device_harness.create(
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

        fake_backend.emit_update(readpv, value=8.25, units="A")
        fake_backend.values[readpv] = 99.0

        assert device_harness.run("daemon", daemon_device.read) == pytest.approx(8.25)


class TestEpicsStringReadable:
    """Behavior tests for string readable EPICS class."""

    def test_string_readable_requests_string_mode_from_backend(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:STR.RBV"
        fake_backend.values[readpv] = "hello"

        device = device_harness.create(
            "daemon",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
            monitor=False,
        )
        value = device_harness.run("daemon", device.read, 0)

        assert value == "hello"
        assert ("get_pv_value", readpv, True) in fake_backend.get_calls

    def test_string_readable_converts_char_waveform_in_callback(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:STR.RBV"
        fake_backend.values[readpv] = ""
        device = device_harness.create(
            "poller",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )

        fake_backend.emit_update(readpv, value=numpy.array([65, 66, 67]), units="")

        assert device_harness.run("poller", device._cache.get, device, "value") == "ABC"

    def test_daemon_string_readable_prefers_cached_value_when_monitor_enabled(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:STR.RBV"
        fake_backend.values[readpv] = "backend-before"

        daemon_device = device_harness.create(
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

        value = device_harness.run("daemon", daemon_device.read)

        assert value == "cached"
        assert len(fake_backend.get_calls) == get_calls_before

    def test_daemon_string_readable_falls_back_to_backend_without_cached_value(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:STR.RBV"
        fake_backend.values[readpv] = "from-backend"
        device = device_harness.create(
            "daemon",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
        )
        get_calls_before = len(fake_backend.get_calls)

        value = device_harness.run("daemon", device.read, 0)

        assert value == "from-backend"
        assert len(fake_backend.get_calls) == get_calls_before + 1

    def test_daemon_string_readable_ignores_cache_when_monitor_disabled(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:STR.RBV"
        fake_backend.values[readpv] = "from-backend"
        device = device_harness.create(
            "daemon",
            EpicsStringReadable,
            name="string_readable",
            readpv=readpv,
            monitor=False,
        )
        device_harness.run("daemon", device._cache.put, device._name, "value", "from-cache")
        get_calls_before = len(fake_backend.get_calls)

        value = device_harness.run("daemon", device.read, 0)

        assert value == "from-backend"
        assert len(fake_backend.get_calls) == get_calls_before + 1
