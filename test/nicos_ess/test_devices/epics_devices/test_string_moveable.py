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

"""Harness tests for EpicsStringMoveable."""

from nicos.core import status

from nicos_ess.devices.epics.pva.epics_devices import EpicsStringMoveable
from test.nicos_ess.test_devices.doubles.epics_pva_backend import (
    string_moveable_config,
)

from .conftest import assert_error_status


class TestEpicsStringMoveable:
    """Behavior tests for string moveable class."""

    def test_daemon_string_moveable_starts_with_string_target(
        self, device_harness, fake_backend
    ):
        config = string_moveable_config()
        config["monitor"] = False
        fake_backend.values[config["readpv"]] = "OFF"
        fake_backend.values[config["writepv"]] = "OFF"
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        device = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **config,
        )
        device_harness.run("daemon", device.start, "ON")

        assert fake_backend.put_calls[-1] == (config["writepv"], "ON", False)
        assert device_harness.run("daemon", device.status, 0) == (status.OK, "ok")

    def test_daemon_string_moveable_status_returns_timeout_error(
        self, device_harness, fake_backend
    ):
        config = string_moveable_config()
        config["monitor"] = False
        fake_backend.values[config["readpv"]] = "OFF"
        fake_backend.values[config["writepv"]] = "OFF"
        fake_backend.get_alarm_status = lambda pv: (_ for _ in ()).throw(TimeoutError())

        device = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **config,
        )
        assert device_harness.run("daemon", device.status, 0) == (
            status.ERROR,
            "timeout reading status",
        )

    def test_poller_string_moveable_value_and_status_callbacks_update_cache(
        self, device_harness, fake_backend
    ):
        config = string_moveable_config()
        fake_backend.values[config["readpv"]] = "OFF"
        fake_backend.values[config["writepv"]] = "OFF"

        device = device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **config,
        )
        fake_backend.emit_update(
            config["readpv"],
            value="ON",
            units="",
            severity=status.WARN,
            message="limit",
        )
        fake_backend.emit_update(config["writepv"], value="ON", units="")

        assert device_harness.run("poller", device._cache.get, device, "value") == "ON"
        assert device_harness.run("poller", device._cache.get, device, "target") == "ON"
        assert device_harness.run("poller", device._cache.get, device, "status") == (
            status.WARN,
            "limit",
        )

    def test_poller_string_moveable_connection_callback_sets_comm_failure(
        self, device_harness, fake_backend
    ):
        config = string_moveable_config()
        fake_backend.values[config["readpv"]] = "OFF"
        fake_backend.values[config["writepv"]] = "OFF"

        device = device_harness.create(
            "poller",
            EpicsStringMoveable,
            name="string_moveable",
            **config,
        )
        fake_backend.emit_connection(config["readpv"], False)

        assert_error_status(
            device_harness.run("poller", device._cache.get, device, "status")
        )

    def test_daemon_string_moveable_prefers_cached_value_and_status_from_poller(
        self, device_harness, fake_backend
    ):
        config = string_moveable_config()
        fake_backend.values[config["readpv"]] = "OFF"
        fake_backend.values[config["writepv"]] = "OFF"
        fake_backend.alarms[config["readpv"]] = (status.OK, "backend-ok")

        daemon_device, _poller_device = device_harness.create_pair(
            EpicsStringMoveable,
            name="string_moveable",
            shared=config,
        )

        fake_backend.emit_update(
            config["readpv"],
            value="ON",
            units="",
            severity=status.WARN,
            message="from-callback",
        )
        fake_backend.values[config["readpv"]] = "BACKEND-STALE"
        get_calls_before = len(fake_backend.get_calls)

        assert device_harness.run("daemon", daemon_device.read) == "ON"
        assert device_harness.run("daemon", daemon_device.status) == (
            status.WARN,
            "from-callback",
        )
        assert len(fake_backend.get_calls) == get_calls_before

    def test_string_moveable_second_start_wins_when_old_callbacks_arrive_late(
        self, device_harness, fake_backend
    ):
        config = string_moveable_config()
        fake_backend.values[config["readpv"]] = "OFF"
        fake_backend.values[config["writepv"]] = "OFF"
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        daemon_device, _poller_device = device_harness.create_pair(
            EpicsStringMoveable,
            name="string_moveable",
            shared=config,
        )

        device_harness.run("daemon", daemon_device.start, "ON")
        device_harness.run("daemon", daemon_device.start, "OFF")
        fake_backend.emit_update(config["writepv"], value="ON", units="")
        fake_backend.emit_update(config["readpv"], value="ON", units="")
        observed_target = device_harness.run("daemon", lambda: daemon_device.target)

        assert observed_target == "OFF"

    def test_string_moveable_out_of_order_callbacks_do_not_swap_last_target(
        self, device_harness, fake_backend
    ):
        config = string_moveable_config()
        fake_backend.values[config["readpv"]] = "OFF"
        fake_backend.values[config["writepv"]] = "OFF"
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        daemon_device, _poller_device = device_harness.create_pair(
            EpicsStringMoveable,
            name="string_moveable",
            shared=config,
        )

        device_harness.run("daemon", daemon_device.start, "ON")
        fake_backend.emit_update(config["writepv"], value="ON", units="")
        fake_backend.emit_update(config["readpv"], value="OFF", units="")
        observed_target = device_harness.run("daemon", lambda: daemon_device.target)

        assert observed_target == "ON"

    def test_string_moveable_finish_warns_if_target_not_reached(
        self, device_harness, fake_backend
    ):
        config = string_moveable_config()
        config["monitor"] = False
        fake_backend.values[config["readpv"]] = "OFF"
        fake_backend.values[config["writepv"]] = "OFF"
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        daemon_device = device_harness.create(
            "daemon",
            EpicsStringMoveable,
            name="string_moveable",
            **config,
        )
        device_harness.run("daemon", daemon_device.start, "ON")

        def _finish_and_capture_warning():
            messages = []
            original_warning = daemon_device.log.warning

            def capture_warning(msg, *args, **kwargs):
                del kwargs
                messages.append(msg % args if args else msg)

            daemon_device.log.warning = capture_warning
            try:
                daemon_device.finish()
            finally:
                daemon_device.log.warning = original_warning
            return messages

        warning_messages = device_harness.run("daemon", _finish_and_capture_warning)

        assert any("did not reach target" in msg for msg in warning_messages)
