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

from nicos_ess.devices.epics import mbbi_direct
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()
    monkeypatch.setattr(mbbi_direct, "create_wrapper", lambda timeout, use_pva: backend)

    backend.values["SIM:MBBI"] = 0
    backend.values["SIM:MBBI.B0"] = 0
    backend.values["SIM:MBBI.B1"] = 0
    backend.values["SIM:MBBIBitNam0"] = "Bit 0"
    backend.values["SIM:MBBIBitNam1"] = "Bit 1"
    return backend


class TestMBBIDirectStatusHarness:
    def test_initializes(self, device_harness, fake_backend):
        del fake_backend
        daemon_device, poller_device = device_harness.create_pair(
            mbbi_direct.MBBIDirectStatus,
            name="mbbi_direct",
            shared={
                "pv_root": "SIM:MBBI",
                "number_of_bits": 2,
                "monitor": True,
                "pva": True,
            },
        )

        assert daemon_device is not None
        assert poller_device is not None
