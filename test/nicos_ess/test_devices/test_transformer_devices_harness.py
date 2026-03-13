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

from nicos_ess.devices import transformer_devices
from nicos_ess.devices.epics.pva import epics_devices
from nicos_ess.devices.epics.pva import motor
from nicos_ess.devices.epics.pva.epics_devices import EpicsManualMappedAnalogMoveable
from test.nicos_ess.test_devices.doubles import (
    FakeEpicsBackend,
    HarnessMoveable,
    seed_epics_jog_motor_defaults,
)


MOTOR_PV = "SIM:M1"


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()
    monkeypatch.setattr(
        epics_devices, "create_wrapper", lambda timeout, use_pva: backend
    )
    monkeypatch.setattr(motor, "create_wrapper", lambda timeout, use_pva: backend)

    backend.values["SIM:CHOP:SPD.RBV"] = 14.0
    backend.values["SIM:CHOP:SPD.VAL"] = 14.0
    seed_epics_jog_motor_defaults(backend, motor_pv=MOTOR_PV)
    return backend


@pytest.fixture
def attached_transformer_devices(device_harness, fake_backend):
    del fake_backend

    device_harness.create_pair(
        HarnessMoveable,
        name="phase_ns_dev",
        shared={"initial": 0.0},
    )
    device_harness.create_pair(
        EpicsManualMappedAnalogMoveable,
        name="mapped_speed_dev",
        shared={
            "readpv": "SIM:CHOP:SPD.RBV",
            "writepv": "SIM:CHOP:SPD.VAL",
            "mapping": {"0 Hz": 0.0, "14 Hz": 14.0},
            "monitor": True,
            "pva": True,
        },
    )
    device_harness.create_pair(
        motor.EpicsJogMotor,
        name="jog_motor",
        shared={
            "motorpv": MOTOR_PV,
            "monitor": True,
            "pva": True,
        },
    )


class TestChopperPhaseHarness:
    def test_initializes(self, device_harness, fake_backend, attached_transformer_devices):
        del fake_backend, attached_transformer_devices
        daemon_device, poller_device = device_harness.create_pair(
            transformer_devices.ChopperPhase,
            name="chopper_phase",
            shared={
                "unit": "deg",
                "offset": 0.0,
                "phase_ns_dev": "phase_ns_dev",
                "mapped_speed_dev": "mapped_speed_dev",
            },
        )

        assert daemon_device is not None
        assert poller_device is not None


class TestDegreesPerSecondToRPMHarness:
    def test_initializes(self, device_harness, fake_backend, attached_transformer_devices):
        del fake_backend, attached_transformer_devices
        daemon_device, poller_device = device_harness.create_pair(
            transformer_devices.DegreesPerSecondToRPM,
            name="degrees_per_second_to_rpm",
            shared={
                "motor": "jog_motor",
            },
        )

        assert daemon_device is not None
        assert poller_device is not None
