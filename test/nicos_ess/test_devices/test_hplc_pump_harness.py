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
from nicos_ess.devices.epics import hplc_pump
from nicos_ess.devices.epics.pva import epics_common
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend

PV_ROOT = "SIM:PUMP:"


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()
    monkeypatch.setattr(
        epics_common, "create_wrapper", lambda timeout, use_pva: backend
    )

    backend.values[f"{PV_ROOT}Error-R"] = 0
    backend.value_choices[f"{PV_ROOT}Error-R"] = ["No error", "Hardware error"]
    backend.values[f"{PV_ROOT}ErrorText-R"] = ""
    backend.values[f"{PV_ROOT}ErrorReset-S"] = 0
    backend.values[f"{PV_ROOT}Status-R"] = 0
    backend.value_choices[f"{PV_ROOT}Status-R"] = ["Off", "Pumping"]
    backend.values[f"{PV_ROOT}PressureMax-S"] = 0.0
    backend.values[f"{PV_ROOT}PressureMax-R"] = 10.0
    backend.values[f"{PV_ROOT}PressureMin-S"] = 0.0
    backend.values[f"{PV_ROOT}PressureMin-R"] = 1.0
    backend.values[f"{PV_ROOT}PumpForTime-S"] = 0
    backend.values[f"{PV_ROOT}PumpForVolume-S"] = 0
    backend.values[f"{PV_ROOT}Start-S"] = 0
    backend.values[f"{PV_ROOT}Stop-S"] = 0
    return backend


class TestHPLCPumpControllerHarness:
    def _create_pair(self, device_harness):
        return device_harness.create_pair(
            hplc_pump.HPLCPumpController,
            name="hplc_pump",
            shared={
                "pv_root": PV_ROOT,
                "monitor": True,
                "pva": True,
            },
        )

    def test_initializes(self, device_harness, fake_backend):
        del fake_backend
        daemon_device, poller_device = self._create_pair(device_harness)

        assert daemon_device is not None
        assert poller_device is not None

    def test_status_busy_while_pumping(self, device_harness, fake_backend):
        daemon_device, _poller_device = self._create_pair(device_harness)

        fake_backend.emit_update(f"{PV_ROOT}Status-R", value=1)

        assert daemon_device.status() == (status.BUSY, "Pumping")

    def test_status_error_from_error_enum(self, device_harness, fake_backend):
        daemon_device, _poller_device = self._create_pair(device_harness)

        fake_backend.emit_update(f"{PV_ROOT}Error-R", value=1)

        assert daemon_device.status() == (status.ERROR, "Hardware error")

    def test_stop_writes_stop_pv(self, device_harness, fake_backend):
        daemon_device, _poller_device = self._create_pair(device_harness)

        daemon_device.stop()

        assert fake_backend.values[f"{PV_ROOT}Stop-S"] == 1

    def test_pressure_limits_read_from_readback_pvs(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = self._create_pair(device_harness)
        del fake_backend

        assert daemon_device.max_pressure == 10.0
        assert daemon_device.min_pressure == 1.0
