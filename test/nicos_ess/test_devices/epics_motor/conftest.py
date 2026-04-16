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

from test.nicos_ess.test_devices.doubles import patch_create_wrapper
from test.nicos_ess.test_devices.epics_motor.helpers import seed_default_motor_pvs


@pytest.fixture
def fake_backend(monkeypatch):
    return patch_create_wrapper(monkeypatch, motor)


@pytest.fixture(autouse=True)
def default_motor_pvs(fake_backend):
    seed_default_motor_pvs(fake_backend)
