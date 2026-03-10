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

from nicos_ess.devices.epics.pva import motor
from nicos_ess.devices.epics.pva.motor import EpicsJogMotor
from test.nicos_ess.test_devices.doubles import (
    patch_create_wrapper,
    seed_epics_jog_motor_defaults,
)


MOTOR_PV = "SIM:M1"
ROLES = ("daemon", "poller")


@pytest.fixture
def fake_backend(monkeypatch):
    backend = patch_create_wrapper(monkeypatch, motor)

    def close_subscription(token):
        if token in backend.subscriptions:
            backend.subscriptions.remove(token)

    backend.close_subscription = close_subscription
    seed_epics_jog_motor_defaults(backend, motor_pv=MOTOR_PV)
    return backend


@pytest.mark.parametrize("role", ROLES)
def test_epics_jog_motor_initializes(role, device_harness, fake_backend):
    del fake_backend
    dev = device_harness.create_master(
        role,
        EpicsJogMotor,
        name=f"epics_jog_motor_{role}",
        motorpv=MOTOR_PV,
        monitor=False,
    )
    assert dev is not None
