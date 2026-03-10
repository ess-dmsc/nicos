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

from nicos_ess.devices.epics import chopper_delay_error
from nicos_ess.devices.epics.pva import epics_devices
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend


ROLES = ("daemon", "poller")


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()
    monkeypatch.setattr(
        epics_devices, "create_wrapper", lambda timeout, use_pva: backend
    )
    backend.values["SIM:CHOP:DELAY"] = [1.0, 2.0, 3.0]
    return backend


@pytest.mark.parametrize("role", ROLES)
def test_chopper_delay_error_initializes(
    role,
    device_harness,
    fake_backend,
):
    del fake_backend
    dev = device_harness.create_master(
        role,
        chopper_delay_error.ChopperDelayError,
        name=f"chopper_delay_error_{role}",
        readpv="SIM:CHOP:DELAY",
    )
    assert dev is not None
