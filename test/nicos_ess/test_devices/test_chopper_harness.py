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

from nicos_ess.devices.epics import chopper as chopper_mod
from nicos_ess.devices.epics.pva import epics_devices
from nicos_ess.devices.epics.pva.epics_devices import EpicsManualMappedAnalogMoveable
from test.nicos_ess.test_devices.doubles import (
    FakeEpicsBackend,
    HarnessMappedMoveable,
    HarnessReadable,
)


ROLES = ("daemon", "poller")


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()

    monkeypatch.setattr(
        chopper_mod, "create_wrapper", lambda timeout, use_pva: backend
    )
    monkeypatch.setattr(
        epics_devices, "create_wrapper", lambda timeout, use_pva: backend
    )

    backend.values["SIM:CHOP:ChopState_R"] = "stop"
    backend.value_choices["SIM:CHOP:ChopState_R"] = [
        "stop",
        "start",
        "a_start",
        "park",
    ]
    backend.values["SIM:ODIN:SPD.RBV"] = 14.0
    backend.values["SIM:ODIN:SPD.VAL"] = 14.0
    return backend


@pytest.fixture
def attached_chopper_devices(device_harness, fake_backend):
    del fake_backend
    for role in ROLES:
        device_harness.create_master(
            role,
            HarnessReadable,
            name="ess_state",
            initial="stop",
        )
        device_harness.create_master(
            role,
            HarnessMappedMoveable,
            name="ess_command",
            mapping={"stop": 0, "start": 1},
        )
        device_harness.create_master(
            role,
            HarnessMappedMoveable,
            name="ess_speed",
            mapping={"0 Hz": 0, "14 Hz": 14},
        )
        device_harness.create_master(
            role,
            HarnessReadable,
            name="ess_chic_conn",
            initial="Connected",
        )
        device_harness.create_master(
            role,
            EpicsManualMappedAnalogMoveable,
            name="odin_speed",
            readpv="SIM:ODIN:SPD.RBV",
            writepv="SIM:ODIN:SPD.VAL",
            mapping={"0 Hz": 0.0, "14 Hz": 14.0},
            monitor=False,
        )


@pytest.mark.parametrize("role", ROLES)
def test_chopper_alarms_initializes(role, device_harness, fake_backend):
    del fake_backend
    dev = device_harness.create_master(
        role,
        chopper_mod.ChopperAlarms,
        name=f"chopper_alarms_{role}",
        pv_root="SIM:CHOP:",
    )
    assert dev is not None


@pytest.mark.parametrize("role", ROLES)
def test_ess_chopper_controller_initializes(
    role,
    device_harness,
    fake_backend,
    attached_chopper_devices,
):
    del fake_backend, attached_chopper_devices
    dev = device_harness.create_master(
        role,
        chopper_mod.EssChopperController,
        name=f"ess_chopper_{role}",
        state="ess_state",
        command="ess_command",
        speed="ess_speed",
        chic_conn="ess_chic_conn",
        mapping={"stop": "stop", "start": "start"},
    )
    assert dev is not None


@pytest.mark.parametrize("role", ROLES)
def test_odin_chopper_controller_initializes(
    role,
    device_harness,
    fake_backend,
    attached_chopper_devices,
):
    del fake_backend, attached_chopper_devices
    dev = device_harness.create_master(
        role,
        chopper_mod.OdinChopperController,
        name=f"odin_chopper_{role}",
        pv_root="SIM:CHOP:",
        speed="odin_speed",
        mapping={"stop": "stop", "start": "start", "a_start": "a_start", "park": "park"},
    )
    assert dev is not None
