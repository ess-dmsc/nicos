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

import pytest

from nicos.core import status
from nicos_ess.devices.epics.pva import motor
from nicos_ess.devices.epics.pva.epics_common import ChannelUpdate
from nicos_ess.devices.epics.pva.motor import EpicsJogMotor
from test.nicos_ess.test_devices.doubles import (
    patch_create_wrapper,
    seed_epics_jog_motor_defaults,
)

MOTOR_PV = "SIM:M1"


@pytest.fixture
def fake_backend(monkeypatch):
    backend = patch_create_wrapper(monkeypatch, motor)

    def close_subscription(token):
        if token in backend.subscriptions:
            backend.subscriptions.remove(token)

    backend.close_subscription = close_subscription
    seed_epics_jog_motor_defaults(backend, motor_pv=MOTOR_PV)
    return backend


@pytest.fixture
def jog_motor(device_harness, fake_backend):
    del fake_backend
    return device_harness.create(
        "daemon",
        EpicsJogMotor,
        name="epics_jog_motor",
        motorpv=MOTOR_PV,
        monitor=False,
        pva=True,
    )


class TestEpicsJogMotorHarness:
    def test_initializes(self, device_harness, fake_backend):
        del fake_backend
        daemon_device, poller_device = device_harness.create_pair(
            EpicsJogMotor,
            name="epics_jog_motor",
            shared={
                "motorpv": MOTOR_PV,
                "monitor": True,
                "pva": True,
            },
        )

        assert daemon_device is not None
        assert poller_device is not None

    @pytest.mark.parametrize(
        ("requested", "expected"),
        [(0.5, 1.0), (5.0, 5.0), (20.0, 10.0)],
    )
    def test_speed_is_clamped_to_hardware_range(
        self, device_harness, jog_motor, requested, expected
    ):
        assert (
            device_harness.run("daemon", jog_motor._get_valid_speed, requested)
            == expected
        )

    @pytest.mark.parametrize(
        ("target", "direction_channel", "expected_direction"),
        [(2.0, ".JOGF", 1), (-2.0, ".JOGR", -1)],
    )
    def test_start_selects_jog_direction(
        self,
        device_harness,
        fake_backend,
        jog_motor,
        target,
        direction_channel,
        expected_direction,
    ):
        device_harness.run("daemon", jog_motor.doStart, target)

        assert fake_backend.values[f"{MOTOR_PV}.JVEL"] == abs(target)
        assert fake_backend.values[f"{MOTOR_PV}{direction_channel}"] == 1
        assert device_harness.run("daemon", getattr, jog_motor, "jog_dir") == (
            expected_direction
        )

    def test_zero_target_stops_jogging(self, device_harness, fake_backend, jog_motor):
        fake_backend.values[f"{MOTOR_PV}.JOGF"] = 1

        device_harness.run("daemon", jog_motor.doStart, 0)

        assert fake_backend.values[f"{MOTOR_PV}.JOGF"] == 0
        assert fake_backend.values[f"{MOTOR_PV}.JOGR"] == 0
        assert fake_backend.values[f"{MOTOR_PV}.STOP"] == 1

    @pytest.mark.parametrize(
        ("moving", "expected_status", "completed"),
        [(0, status.OK, True), (1, status.BUSY, False)],
    )
    def test_moving_state_controls_status_and_completion(
        self,
        device_harness,
        fake_backend,
        jog_motor,
        moving,
        expected_status,
        completed,
    ):
        fake_backend.values[f"{MOTOR_PV}.DMOV"] = int(not moving)
        fake_backend.values[f"{MOTOR_PV}.MOVN"] = moving

        observed_status = device_harness.run("daemon", jog_motor._compute_status, 0)

        assert observed_status[0] == expected_status
        assert device_harness.run("daemon", jog_motor.doIsCompleted) is completed

    def test_velocity_update_keeps_current_direction(self, device_harness, jog_motor):
        device_harness.run("daemon", jog_motor._setROParam, "jog_dir", -1)

        device_harness.run(
            "daemon",
            jog_motor._on_channel_update,
            ChannelUpdate("jog_velocity", 2.0),
        )

        assert (
            device_harness.run("daemon", jog_motor._cache.get, jog_motor, "value")
            == -2.0
        )
        assert (
            device_harness.run("daemon", jog_motor._cache.get, jog_motor, "target")
            == -2.0
        )

    def test_velocity_update_while_stopped_keeps_value_at_zero(
        self, device_harness, jog_motor
    ):
        device_harness.run(
            "daemon",
            jog_motor._on_channel_update,
            ChannelUpdate("jog_velocity", 2.0),
        )

        assert (
            device_harness.run("daemon", jog_motor._cache.get, jog_motor, "value")
            == 0.0
        )
        assert (
            device_harness.run("daemon", jog_motor._cache.get, jog_motor, "target")
            == 0.0
        )

    def test_direction_update_sets_signed_velocity(
        self, device_harness, fake_backend, jog_motor
    ):
        fake_backend.values[f"{MOTOR_PV}.JVEL"] = 2.0

        device_harness.run(
            "daemon",
            jog_motor._on_channel_update,
            ChannelUpdate("jogreverse", 1),
        )

        assert device_harness.run("daemon", getattr, jog_motor, "jog_dir") == -1
        assert (
            device_harness.run("daemon", jog_motor._cache.get, jog_motor, "value")
            == -2.0
        )
        assert (
            device_harness.run("daemon", jog_motor._cache.get, jog_motor, "target")
            == -2.0
        )

    def test_stop_publishes_zero_value_and_target(self, device_harness, jog_motor):
        device_harness.run("daemon", jog_motor._setROParam, "jog_dir", 1)
        device_harness.run("daemon", jog_motor._setROParam, "target", 2.0)

        device_harness.run("daemon", jog_motor.doStop)

        assert (
            device_harness.run("daemon", jog_motor._cache.get, jog_motor, "value")
            == 0.0
        )
        assert (
            device_harness.run("daemon", jog_motor._cache.get, jog_motor, "target")
            == 0.0
        )

    def test_status_reports_lost_connection(
        self, device_harness, fake_backend, jog_motor
    ):
        fake_backend.disconnect_backend()

        assert device_harness.run("daemon", jog_motor._compute_status, 0) == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )
