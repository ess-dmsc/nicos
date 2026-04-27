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

"""Harness tests for EpicsMappedReadable, EpicsMappedMoveable, and
EpicsManualMappedAnalogMoveable."""

import pytest

from nicos.core import MoveError, status

from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsManualMappedAnalogMoveable,
    EpicsMappedMoveable,
    EpicsMappedReadable,
)
from test.nicos_ess.test_devices.doubles.epics_pva_backend import (
    analog_moveable_config,
    mapped_config,
)

from .conftest import manual_moveable_config


# ---------------------------------------------------------------------------
# MappedReadable
# ---------------------------------------------------------------------------


class TestEpicsMappedReadable:
    """Behavior tests for mapped readable class."""

    def test_daemon_mapped_readable_initializes_mapping_from_choices(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:MAP.RBV"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = "ON"

        device = device_harness.create(
            "daemon",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
            monitor=False,
        )

        assert device_harness.run("daemon", lambda: device.mapping) == {
            "OFF": 0,
            "ON": 1,
        }
        assert device_harness.run("daemon", device.read, 0) == "ON"

    def test_poller_mapped_readable_callback_loads_mapping_lazily(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:MAP.RBV"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = 0

        device = device_harness.create(
            "poller",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )
        fake_backend.emit_update(readpv, value=1, units="")

        assert device_harness.run("poller", lambda: device.mapping) == {
            "OFF": 0,
            "ON": 1,
        }
        assert device_harness.run("poller", device._cache.get, device, "value") == "ON"

    def test_daemon_mapped_readable_prefers_cached_value_when_monitor_enabled(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:MAP.RBV"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = 0

        daemon_device = device_harness.create(
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

        assert device_harness.run("daemon", daemon_device.read) == "ON"
        assert len(fake_backend.get_calls) == get_calls_before

    def test_mapped_readable_unknown_callback_value_is_forwarded_as_raw(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:MAP:UNKNOWN.RBV"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = 0

        device = device_harness.create(
            "poller",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )

        fake_backend.emit_update(readpv, value=99, units="")

        assert device_harness.run("poller", device._cache.get, device, "value") == 99

    def test_daemon_mapped_readable_direct_read_applies_mapping_to_raw_numeric_value(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:MAP.RBV"
        fake_backend.value_choices[readpv] = ["OFF", "ON", "TWO", "THREE"]
        fake_backend.values[readpv] = 3

        device = device_harness.create(
            "daemon",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
            monitor=False,
        )

        assert device_harness.run("daemon", lambda: device._inverse_mapping) == {
            0: "OFF",
            1: "ON",
            2: "TWO",
            3: "THREE",
        }
        assert device_harness.run("daemon", device.read, 0) == "THREE"

    def test_mapped_readable_first_read_before_monitor_callback_returns_mapped_value(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:MAP.RBV"
        fake_backend.value_choices[readpv] = ["OFF", "ON", "TWO", "THREE"]
        fake_backend.values[readpv] = 3

        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMappedReadable,
            name="mapped_readable",
            shared={"readpv": readpv},
        )

        assert device_harness.run("daemon", daemon_device.read) == "THREE"

    def test_mapped_readable_callback_maps_string_typed_raw_when_inverse_uses_int_keys(
        self, device_harness, fake_backend
    ):
        readpv = "SIM:MAP.RBV"
        fake_backend.value_choices[readpv] = ["OFF", "ON"]
        fake_backend.values[readpv] = 0

        device = device_harness.create(
            "poller",
            EpicsMappedReadable,
            name="mapped_readable",
            readpv=readpv,
        )

        fake_backend.emit_update(readpv, value="1", units="")

        assert device_harness.run("poller", device._cache.get, device, "value") == "ON"


# ---------------------------------------------------------------------------
# MappedMoveable
# ---------------------------------------------------------------------------


class TestEpicsMappedMoveable:
    """Behavior tests for mapped moveable class."""

    def test_daemon_mapped_moveable_maps_user_target_to_raw_value(
        self, device_harness, fake_backend
    ):
        config = mapped_config()
        fake_backend.value_choices[config["readpv"]] = ["OFF", "ON"]
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0

        device = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
            monitor=False,
        )
        device_harness.run("daemon", device.start, "ON")

        assert device_harness.run("daemon", lambda: device.mapping) == {
            "OFF": 0,
            "ON": 1,
        }
        assert fake_backend.put_calls[-1] == (config["writepv"], 1, False)

    def test_poller_mapped_moveable_callback_maps_readback_and_target(
        self, device_harness, fake_backend
    ):
        config = mapped_config()
        fake_backend.value_choices[config["readpv"]] = ["OFF", "ON"]
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0

        device = device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
            mapping=config["mapping"],
        )
        fake_backend.emit_update(config["readpv"], value=1, units="")
        fake_backend.emit_update(config["writepv"], value=1, units="")

        assert device_harness.run("poller", device._cache.get, device, "value") == "ON"
        assert device_harness.run("poller", device._cache.get, device, "target") == 1

    def test_daemon_mapped_moveable_prefers_cached_readback_from_poller(
        self, device_harness, fake_backend
    ):
        config = mapped_config()
        fake_backend.value_choices[config["readpv"]] = ["OFF", "ON"]
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0

        daemon_device = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
        )
        fake_backend.emit_update(config["readpv"], value=1, units="")
        fake_backend.values[config["readpv"]] = 0
        get_calls_before = len(fake_backend.get_calls)

        assert device_harness.run("daemon", daemon_device.read) == "ON"
        assert len(fake_backend.get_calls) == get_calls_before

    def test_mapped_moveable_second_start_wins_when_old_callbacks_arrive_late(
        self, device_harness, fake_backend
    ):
        config = mapped_config()
        fake_backend.value_choices[config["readpv"]] = ["OFF", "ON"]
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        daemon_device = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
            mapping=config["mapping"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
            mapping=config["mapping"],
        )

        device_harness.run("daemon", daemon_device.start, "ON")
        device_harness.run("daemon", daemon_device.start, "OFF")
        fake_backend.emit_update(config["writepv"], value=1, units="")
        fake_backend.emit_update(config["readpv"], value=1, units="")
        observed_target = device_harness.run("daemon", lambda: daemon_device.target)

        assert observed_target == "OFF"

    def test_mapped_moveable_unknown_callback_value_is_forwarded_as_raw(
        self, device_harness, fake_backend
    ):
        config = mapped_config()
        fake_backend.value_choices[config["readpv"]] = ["OFF", "ON"]
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0

        device = device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
            mapping=config["mapping"],
        )

        fake_backend.emit_update(config["readpv"], value=99, units="")

        assert device_harness.run("poller", device._cache.get, device, "value") == 99

    def test_mapped_moveable_out_of_order_callbacks_do_not_swap_last_target(
        self, device_harness, fake_backend
    ):
        config = mapped_config()
        fake_backend.value_choices[config["readpv"]] = ["OFF", "ON"]
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")
        daemon_device = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
            mapping=config["mapping"],
        )
        device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
            mapping=config["mapping"],
        )

        device_harness.run("daemon", daemon_device.start, "ON")
        fake_backend.emit_update(config["writepv"], value=1, units="")
        fake_backend.emit_update(config["readpv"], value=0, units="")
        observed_target = device_harness.run("daemon", lambda: daemon_device.target)

        assert observed_target == "ON"

    def test_daemon_mapped_moveable_direct_read_applies_mapping_to_raw_numeric_value(
        self, device_harness, fake_backend
    ):
        config = mapped_config()
        config["mapping"] = {"OFF": 0, "ON": 1, "TWO": 2, "THREE": 3}
        fake_backend.value_choices[config["readpv"]] = [
            "OFF",
            "ON",
            "TWO",
            "THREE",
        ]
        fake_backend.values[config["readpv"]] = 3
        fake_backend.values[config["writepv"]] = 0

        device = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
            mapping=config["mapping"],
            monitor=False,
        )

        assert device_harness.run("daemon", lambda: device._inverse_mapping) == {
            0: "OFF",
            1: "ON",
            2: "TWO",
            3: "THREE",
        }
        assert device_harness.run("daemon", device.read, 0) == "THREE"

    def test_mapped_moveable_first_read_before_monitor_callback_returns_mapped_value(
        self, device_harness, fake_backend
    ):
        config = mapped_config()
        config["mapping"] = {"OFF": 0, "ON": 1, "TWO": 2, "THREE": 3}
        fake_backend.value_choices[config["readpv"]] = [
            "OFF",
            "ON",
            "TWO",
            "THREE",
        ]
        fake_backend.values[config["readpv"]] = 3
        fake_backend.values[config["writepv"]] = 0

        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMappedMoveable,
            name="mapped_moveable",
            shared=config,
        )

        assert device_harness.run("daemon", daemon_device.read) == "THREE"

    def test_mapped_moveable_callback_maps_string_typed_raw_when_inverse_uses_int_keys(
        self, device_harness, fake_backend
    ):
        config = mapped_config()
        fake_backend.value_choices[config["readpv"]] = ["OFF", "ON"]
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0

        device = device_harness.create(
            "poller",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
            mapping=config["mapping"],
        )

        fake_backend.emit_update(config["readpv"], value="1", units="")

        assert device_harness.run("poller", device._cache.get, device, "value") == "ON"

    def test_mapped_moveable_finish_warns_if_target_not_reached(
        self, device_harness, fake_backend
    ):
        config = mapped_config()
        config["monitor"] = False
        fake_backend.value_choices[config["readpv"]] = ["OFF", "ON"]
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        daemon_device = device_harness.create(
            "daemon",
            EpicsMappedMoveable,
            name="mapped_moveable",
            readpv=config["readpv"],
            writepv=config["writepv"],
            mapping=config["mapping"],
            monitor=False,
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


# ---------------------------------------------------------------------------
# ManualMappedAnalogMoveable
# ---------------------------------------------------------------------------


class TestEpicsManualMappedAnalogMoveable:
    """Behavior tests for manual mapped analog moveable class."""

    def test_daemon_manual_mapped_writes_busy_status_and_raw_target(
        self, device_harness, fake_backend
    ):
        config = analog_moveable_config()
        config["mapping"] = {"0 Hz": 0, "10 Hz": 10}
        config["monitor"] = False
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0
        fake_backend.units[config["readpv"]] = "Hz"
        fake_backend.limits[config["writepv"]] = (0, 20)

        device = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **config,
        )

        device_harness.run("daemon", device.start, "10 Hz")

        assert fake_backend.put_calls[-1] == (config["writepv"], 10, False)
        assert device_harness.run("daemon", device._cache.get, device, "status")[0] == (
            status.BUSY
        )
        assert device_harness.run("daemon", device.doReadTarget) == "10 Hz"

    def test_poller_manual_mapped_callbacks_update_status_and_limits(
        self, device_harness, fake_backend
    ):
        config = analog_moveable_config()
        config["mapping"] = {"0 Hz": 0, "10 Hz": 10}
        config["targetpv"] = "SIM:MAP.TARGET"
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0
        fake_backend.values[config["targetpv"]] = 0
        fake_backend.units[config["readpv"]] = "Hz"
        fake_backend.limits[config["writepv"]] = (0, 20)

        device = device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **config,
        )

        fake_backend.emit_update(config["readpv"], value=3, units="Hz")
        fake_backend.emit_update(config["targetpv"], value=10)
        fake_backend.emit_update(config["writepv"], value=10, limits=(0, 20))

        assert device_harness.run("poller", device._cache.get, device, "value") == 3
        assert device_harness.run("poller", device._cache.get, device, "abslimits") == (
            0,
            20,
        )
        assert device_harness.run("poller", device._cache.get, device, "status")[0] == (
            status.BUSY
        )

        fake_backend.emit_update(config["readpv"], value=10, units="Hz")
        assert device_harness.run("poller", device._cache.get, device, "status")[0] == (
            status.OK
        )

    def test_daemon_manual_mapped_reads_poller_status_transitions(
        self, device_harness, fake_backend
    ):
        config = analog_moveable_config()
        config["mapping"] = {"0 Hz": 0, "10 Hz": 10}
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0
        fake_backend.units[config["readpv"]] = "Hz"

        daemon_device, _poller_device = device_harness.create_pair(
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            shared=config,
        )

        device_harness.run("daemon", daemon_device.start, "10 Hz")
        assert device_harness.run("daemon", daemon_device.status, 0)[0] == status.BUSY

        fake_backend.emit_update(config["readpv"], value=10, units="Hz")
        fake_backend.emit_update(config["writepv"], value=10, limits=(0, 20))
        assert device_harness.run("daemon", daemon_device.status, 0)[0] == status.OK

        fake_backend.emit_update(config["readpv"], value=5, units="Hz")
        assert device_harness.run("daemon", daemon_device.status, 0)[0] == status.BUSY

    def test_daemon_manual_mapped_read_prefers_cached_value_when_monitor_enabled(
        self, device_harness, fake_backend
    ):
        config = analog_moveable_config()
        config["mapping"] = {"0 Hz": 0, "10 Hz": 10}
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0
        fake_backend.units[config["readpv"]] = "Hz"

        daemon_device, _poller_device = device_harness.create_pair(
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            shared=config,
        )

        fake_backend.emit_update(config["readpv"], value=10, units="Hz")
        fake_backend.values[config["readpv"]] = 0
        get_calls_before = len(fake_backend.get_calls)

        assert device_harness.run("daemon", daemon_device.read) == 10
        assert len(fake_backend.get_calls) == get_calls_before

    def test_manual_mapped_warn_alarm_while_moving_does_not_complete_wait(
        self, device_harness, fake_backend
    ):
        config = manual_moveable_config()
        fake_backend.values[config["readpv"]] = 28
        fake_backend.values[config["writepv"]] = 28
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        daemon_device, _poller_device = device_harness.create_pair(
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            shared=config,
        )
        device_harness.run("daemon", daemon_device.start, "14 Hz")
        fake_backend.alarms[config["readpv"]] = (status.WARN, "limit warning")

        observed_status = device_harness.run("daemon", daemon_device.status, 0)
        completed = device_harness.run("daemon", daemon_device.isCompleted)

        assert observed_status[0] == status.BUSY
        assert completed is False

    def test_manual_mapped_maw_recovers_from_transient_disconnect(
        self, device_harness, fake_backend
    ):
        config = manual_moveable_config()
        fake_backend.values[config["readpv"]] = 28
        fake_backend.values[config["writepv"]] = 28
        fake_backend.units[config["readpv"]] = "Hz"
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        daemon_device, _poller_device = device_harness.create_pair(
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            shared=config,
        )

        def _flap_then_recover():
            from nicos import session as active_session

            original_delay = active_session.delay
            delay_calls = {"count": 0}

            def controlled_delay(seconds):
                delay_calls["count"] += 1
                if delay_calls["count"] == 1:
                    fake_backend.emit_connection(config["readpv"], False)
                    fake_backend.emit_connection(config["readpv"], True)
                    fake_backend.emit_update(config["readpv"], value=14, units="Hz")
                    fake_backend.emit_update(config["writepv"], value=14, limits=(0, 40))
                if delay_calls["count"] > 20:
                    raise RuntimeError("test guard: maw did not recover")
                return original_delay(seconds)

            active_session.delay = controlled_delay
            try:
                return daemon_device.maw("14 Hz"), delay_calls["count"]
            finally:
                active_session.delay = original_delay

        value, delay_calls = device_harness.run("daemon", _flap_then_recover)

        assert delay_calls >= 1
        assert value == 14

    def test_manual_mapped_out_of_order_callbacks_keep_busy_until_readback_arrives(
        self, device_harness, fake_backend
    ):
        config = manual_moveable_config()
        fake_backend.values[config["readpv"]] = 28
        fake_backend.values[config["writepv"]] = 28
        fake_backend.units[config["readpv"]] = "Hz"
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        daemon_device, _poller_device = device_harness.create_pair(
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            shared=config,
        )

        device_harness.run("daemon", daemon_device.start, "14 Hz")
        fake_backend.emit_update(config["writepv"], value=14, limits=(0, 40))
        status_after_write = device_harness.run("daemon", daemon_device.status, 0)
        fake_backend.emit_update(config["readpv"], value=14, units="Hz")
        status_after_read = device_harness.run("daemon", daemon_device.status, 0)

        assert status_after_write[0] == status.BUSY
        assert status_after_read[0] == status.OK

    def test_manual_mapped_finish_warns_if_target_not_reached(
        self, device_harness, fake_backend
    ):
        config = manual_moveable_config()
        config["monitor"] = False
        fake_backend.values[config["readpv"]] = 28
        fake_backend.values[config["writepv"]] = 28
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        daemon_device = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **config,
        )
        device_harness.run("daemon", daemon_device.start, "14 Hz")

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

    def test_manual_mapped_status_message_uses_current_target_not_previous_one(
        self, device_harness, fake_backend
    ):
        config = analog_moveable_config()
        config["mapping"] = {"14 Hz": 14, "28 Hz": 28}
        fake_backend.values[config["readpv"]] = 28
        fake_backend.values[config["writepv"]] = 28
        fake_backend.units[config["readpv"]] = "Hz"
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        daemon_device = device_harness.create(
            "daemon",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **config,
        )
        poller_device = device_harness.create(
            "poller",
            EpicsManualMappedAnalogMoveable,
            name="manual_mapped",
            **config,
        )

        device_harness.run("poller", poller_device._setROParam, "target", "28 Hz")

        device_harness.run("daemon", daemon_device.start, "14 Hz")
        fake_backend.emit_update(config["readpv"], value=28, units="Hz")
        st = device_harness.run("daemon", daemon_device.status)

        assert st[0] == status.BUSY
        assert "14" in st[1]
