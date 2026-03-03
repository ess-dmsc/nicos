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

"""Harness tests for EpicsAnalogMoveable and EpicsDigitalMoveable."""

import pytest

from nicos.core import MoveError, status

from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsAnalogMoveable,
    EpicsDigitalMoveable,
)
from test.nicos_ess.test_devices.doubles.epics_pva_backend import (
    analog_moveable_config,
)

from .conftest import assert_error_status, create_analog_pair


# ---------------------------------------------------------------------------
# Analog-specific tests
# ---------------------------------------------------------------------------


class TestEpicsAnalogMoveable:
    """Behavior tests for floating-point moveable class."""

    def test_daemon_analog_moveable_reads_writes_and_status_transitions(
        self, device_harness, fake_backend
    ):
        config = analog_moveable_config()
        config["monitor"] = False
        fake_backend.values[config["readpv"]] = 1.5
        fake_backend.values[config["writepv"]] = 1.5
        fake_backend.units[config["readpv"]] = "mm"
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")
        fake_backend.limits[config["writepv"]] = (-100.0, 100.0)

        daemon_device = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **config,
        )
        device_harness.run("daemon", daemon_device.start, 7.0)

        assert fake_backend.connect_calls == [config["readpv"], config["writepv"]]
        assert fake_backend.put_calls[-1] == (config["writepv"], 7.0, False)
        assert device_harness.run("daemon", daemon_device.status, 0)[0] == status.BUSY
        fake_backend.values[config["readpv"]] = 7.0
        assert device_harness.run("daemon", daemon_device.status, 0)[0] == status.OK
        assert device_harness.run("daemon", lambda: daemon_device.abslimits) == (
            -100.0,
            100.0,
        )

    def test_daemon_analog_moveable_status_returns_timeout_error(
        self, device_harness, fake_backend
    ):
        config = analog_moveable_config()
        config["monitor"] = False
        fake_backend.values[config["readpv"]] = 1.0
        fake_backend.values[config["writepv"]] = 1.0
        fake_backend.get_alarm_status = lambda pv: (_ for _ in ()).throw(TimeoutError())

        daemon_device = device_harness.create(
            "daemon",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **config,
        )

        assert device_harness.run("daemon", daemon_device.status, 0) == (
            status.ERROR,
            "timeout reading status",
        )

    def test_poller_analog_moveable_callbacks_cache_target_limits_and_status(
        self, device_harness, fake_backend
    ):
        config = analog_moveable_config()
        config["targetpv"] = "SIM:M1.TARGET"
        fake_backend.values[config["readpv"]] = 2.0
        fake_backend.values[config["writepv"]] = 2.0
        fake_backend.values[config["targetpv"]] = 2.0
        fake_backend.units[config["readpv"]] = "mm"
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        poller_device = device_harness.create(
            "poller",
            EpicsAnalogMoveable,
            name="analog_moveable",
            **config,
        )

        fake_backend.emit_update(
            config["readpv"],
            value=3.0,
            units="mm",
            severity=status.WARN,
            message="alarm",
        )
        fake_backend.emit_update(config["writepv"], value=3.5, limits=(-10.0, 10.0))
        fake_backend.emit_update(config["targetpv"], value=3.5)

        assert len(fake_backend.subscriptions) == 4
        assert device_harness.run("poller", poller_device._cache.get, poller_device, "value") == pytest.approx(
            3.0
        )
        assert device_harness.run("poller", poller_device._cache.get, poller_device, "unit") == "mm"
        assert device_harness.run("poller", poller_device._cache.get, poller_device, "abslimits") == (
            -10.0,
            10.0,
        )
        assert device_harness.run("poller", poller_device._cache.get, poller_device, "target") == pytest.approx(
            3.5
        )
        assert device_harness.run("poller", poller_device._cache.get, poller_device, "status")[0] == (
            status.BUSY
        )

        fake_backend.emit_connection(config["readpv"], False)
        assert_error_status(
            device_harness.run("poller", poller_device._cache.get, poller_device, "status")
        )

    def test_daemon_analog_moveable_reads_shared_cache_from_poller(
        self, device_harness, fake_backend
    ):
        config = analog_moveable_config()
        fake_backend.values[config["readpv"]] = 0.0
        fake_backend.values[config["writepv"]] = 0.0
        fake_backend.units[config["readpv"]] = "mm"
        fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

        daemon_device, _poller_device = device_harness.create_pair(
            EpicsAnalogMoveable,
            name="analog_moveable",
            shared=config,
        )

        device_harness.run("daemon", daemon_device.start, 5.0)
        fake_backend.emit_update(config["writepv"], value=5.0, limits=(-100.0, 100.0))
        fake_backend.emit_update(config["readpv"], value=5.0, units="mm")
        fake_backend.values[config["readpv"]] = 999.0

        assert device_harness.run("daemon", daemon_device.status)[0] == status.OK
        assert device_harness.run("daemon", daemon_device.read) == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Digital-specific tests
# ---------------------------------------------------------------------------


class TestEpicsDigitalMoveable:
    """Behavior tests for integer moveable variant."""

    def test_digital_moveable_converts_start_target_to_int(
        self, device_harness, fake_backend
    ):
        config = analog_moveable_config()
        config["monitor"] = False
        fake_backend.values[config["readpv"]] = 0
        fake_backend.values[config["writepv"]] = 0
        fake_backend.units[config["readpv"]] = "mm"
        fake_backend.limits[config["writepv"]] = (-10, 10)

        device = device_harness.create(
            "daemon",
            EpicsDigitalMoveable,
            name="digital_moveable",
            **config,
        )
        device_harness.run("daemon", device.start, "7")

        assert fake_backend.put_calls[-1] == (config["writepv"], 7, False)
        assert isinstance(fake_backend.put_calls[-1][1], int)
        assert device_harness.run("daemon", lambda: device.fmtstr) == "%d"


# ---------------------------------------------------------------------------
# Parametrized tests shared between Analog and Digital moveables
# ---------------------------------------------------------------------------

_MOVEABLE_PARAMS = [
    (EpicsAnalogMoveable, 28.0, 14.0, "analog_moveable"),
    (EpicsDigitalMoveable, 28, 14, "digital_moveable"),
]
_MOVEABLE_IDS = ["analog", "digital"]


@pytest.mark.parametrize(
    "device_class,initial_value,target_value,device_name",
    _MOVEABLE_PARAMS,
    ids=_MOVEABLE_IDS,
)
def test_moveable_stale_cache_does_not_complete_move_wait(
    device_harness, fake_backend, device_class, initial_value, target_value, device_name
):
    config = analog_moveable_config()
    fake_backend.values[config["readpv"]] = initial_value
    fake_backend.values[config["writepv"]] = initial_value
    fake_backend.units[config["readpv"]] = "mm"
    fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

    daemon_device, _poller_device = device_harness.create_pair(
        device_class,
        name="moveable",
        shared=config,
    )

    fake_backend.emit_update(config["writepv"], value=initial_value, limits=(-100.0, 100.0))
    fake_backend.emit_update(
        config["readpv"],
        value=initial_value,
        units="mm",
        severity=status.OK,
        message="idle",
    )

    device_harness.run("daemon", daemon_device.start, target_value)
    completed = device_harness.run("daemon", daemon_device.isCompleted)
    move_status = device_harness.run("daemon", daemon_device.status, 0)

    assert completed is False
    assert move_status[0] == status.BUSY


@pytest.mark.parametrize(
    "device_class,initial_value,target_value,device_name",
    _MOVEABLE_PARAMS,
    ids=_MOVEABLE_IDS,
)
def test_moveable_completion_uses_fresh_readback(
    device_harness, fake_backend, device_class, initial_value, target_value, device_name
):
    config = analog_moveable_config()
    fake_backend.values[config["readpv"]] = initial_value
    fake_backend.values[config["writepv"]] = initial_value
    fake_backend.units[config["readpv"]] = "mm"
    fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

    daemon_device, _poller_device = device_harness.create_pair(
        device_class,
        name="moveable",
        shared=config,
    )
    fake_backend.emit_update(config["readpv"], value=initial_value, units="mm")

    device_harness.run("daemon", daemon_device.start, target_value)
    fake_backend.values[config["readpv"]] = target_value
    completed = device_harness.run("daemon", daemon_device.isCompleted)

    assert completed is True


@pytest.mark.parametrize(
    "device_class,initial_value,target_value,device_name",
    _MOVEABLE_PARAMS,
    ids=_MOVEABLE_IDS,
)
def test_moveable_second_start_wins_when_old_callbacks_arrive_late(
    device_harness, fake_backend, device_class, initial_value, target_value, device_name
):
    config = analog_moveable_config()
    fake_backend.values[config["readpv"]] = 0.0 if isinstance(initial_value, float) else 0
    fake_backend.values[config["writepv"]] = 0.0 if isinstance(initial_value, float) else 0
    fake_backend.units[config["readpv"]] = "mm"
    fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

    daemon_device, _poller_device = device_harness.create_pair(
        device_class,
        name=device_name,
        shared=config,
    )

    device_harness.run("daemon", daemon_device.start, initial_value)
    device_harness.run("daemon", daemon_device.start, target_value)
    fake_backend.emit_update(config["writepv"], value=initial_value, limits=(-100.0, 100.0))
    fake_backend.emit_update(config["readpv"], value=initial_value, units="mm")
    observed_target = device_harness.run("daemon", lambda: daemon_device.target)
    observed_status = device_harness.run("daemon", daemon_device.status, 0)

    assert observed_target == target_value
    assert observed_status[0] == status.BUSY
    assert str(int(target_value)) in observed_status[1]


@pytest.mark.parametrize(
    "device_class,initial_value,target_value,device_name",
    _MOVEABLE_PARAMS,
    ids=_MOVEABLE_IDS,
)
def test_moveable_maw_raises_moveerror_on_disconnect(
    device_harness, fake_backend, device_class, initial_value, target_value, device_name
):
    config = analog_moveable_config()
    fake_backend.values[config["readpv"]] = initial_value
    fake_backend.values[config["writepv"]] = initial_value
    fake_backend.units[config["readpv"]] = "mm"
    fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

    daemon_device, _poller_device = device_harness.create_pair(
        device_class,
        name=device_name,
        shared=config,
    )

    def _disconnect_during_wait():
        from nicos import session as active_session

        original_delay = active_session.delay
        delay_calls = {"count": 0}

        def controlled_delay(seconds):
            delay_calls["count"] += 1
            if delay_calls["count"] == 1:
                fake_backend.emit_connection(config["readpv"], False)
            if delay_calls["count"] > 20:
                raise RuntimeError("test guard: maw did not fail on disconnect")
            return original_delay(seconds)

        active_session.delay = controlled_delay
        try:
            with pytest.raises(MoveError):
                daemon_device.maw(target_value)
        finally:
            active_session.delay = original_delay
        return delay_calls["count"]

    delay_calls = device_harness.run("daemon", _disconnect_during_wait)

    assert delay_calls >= 1


@pytest.mark.parametrize(
    "device_class,initial_value,target_value,device_name",
    _MOVEABLE_PARAMS,
    ids=_MOVEABLE_IDS,
)
def test_moveable_maw_recovers_from_transient_disconnect(
    device_harness, fake_backend, device_class, initial_value, target_value, device_name
):
    config = analog_moveable_config()
    fake_backend.values[config["readpv"]] = initial_value
    fake_backend.values[config["writepv"]] = initial_value
    fake_backend.units[config["readpv"]] = "mm"
    fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

    daemon_device, _poller_device = device_harness.create_pair(
        device_class,
        name=device_name,
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
                fake_backend.emit_update(config["readpv"], value=target_value, units="mm")
                fake_backend.emit_update(
                    config["writepv"], value=target_value, limits=(-100.0, 100.0)
                )
            if delay_calls["count"] > 20:
                raise RuntimeError("test guard: maw did not recover")
            return original_delay(seconds)

        active_session.delay = controlled_delay
        try:
            return daemon_device.maw(target_value), delay_calls["count"]
        finally:
            active_session.delay = original_delay

    value, delay_calls = device_harness.run("daemon", _flap_then_recover)

    assert delay_calls >= 1
    assert value == target_value


@pytest.mark.parametrize(
    "device_class,initial_value,target_value,device_name",
    _MOVEABLE_PARAMS,
    ids=_MOVEABLE_IDS,
)
def test_moveable_error_alarm_aborts_completion(
    device_harness, fake_backend, device_class, initial_value, target_value, device_name
):
    config = analog_moveable_config()
    fake_backend.values[config["readpv"]] = initial_value
    fake_backend.values[config["writepv"]] = initial_value
    fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

    daemon_device, _poller_device = device_harness.create_pair(
        device_class,
        name=device_name,
        shared=config,
    )
    device_harness.run("daemon", daemon_device.start, target_value)
    fake_backend.alarms[config["readpv"]] = (status.ERROR, "trip")

    assert device_harness.run("daemon", daemon_device.status, 0)[0] == status.ERROR
    with pytest.raises(MoveError):
        device_harness.run("daemon", daemon_device.isCompleted)


@pytest.mark.parametrize(
    "device_class,initial_value,target_value,device_name",
    _MOVEABLE_PARAMS,
    ids=_MOVEABLE_IDS,
)
def test_moveable_out_of_order_callbacks_keep_busy(
    device_harness, fake_backend, device_class, initial_value, target_value, device_name
):
    config = analog_moveable_config()
    fake_backend.values[config["readpv"]] = initial_value
    fake_backend.values[config["writepv"]] = initial_value
    fake_backend.units[config["readpv"]] = "mm"
    fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

    daemon_device, _poller_device = device_harness.create_pair(
        device_class,
        name=device_name,
        shared=config,
    )

    device_harness.run("daemon", daemon_device.start, target_value)
    fake_backend.emit_update(config["writepv"], value=target_value, limits=(-100.0, 100.0))
    status_after_write = device_harness.run("daemon", daemon_device.status, 0)
    fake_backend.emit_update(config["readpv"], value=target_value, units="mm")
    status_after_read = device_harness.run("daemon", daemon_device.status, 0)

    assert status_after_write[0] == status.BUSY
    assert status_after_read[0] == status.OK


@pytest.mark.parametrize(
    "device_class,initial_value,target_value,device_name",
    _MOVEABLE_PARAMS,
    ids=_MOVEABLE_IDS,
)
def test_moveable_finish_warns_if_target_not_reached(
    device_harness, fake_backend, device_class, initial_value, target_value, device_name
):
    config = analog_moveable_config()
    config["monitor"] = False
    fake_backend.values[config["readpv"]] = initial_value
    fake_backend.values[config["writepv"]] = initial_value
    fake_backend.alarms[config["readpv"]] = (status.OK, "ok")

    daemon_device = device_harness.create(
        "daemon",
        device_class,
        name=device_name,
        **config,
    )
    device_harness.run("daemon", daemon_device.start, target_value)

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
