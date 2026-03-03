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

"""Shared fixtures and helpers for EPICS device harness tests."""

import pytest

from nicos.core import status

from nicos_ess.devices.epics.pva import epics_devices
from nicos_ess.devices.epics.pva.epics_devices import EpicsAnalogMoveable
from test.nicos_ess.test_devices.doubles.epics_pva_backend import (
    analog_moveable_config,
)


@pytest.fixture
def fake_backend(fake_epics_backend_factory):
    """Install a reusable fake EPICS backend for this EPICS module."""
    return fake_epics_backend_factory(epics_devices)


def assert_error_status(observed_status):
    assert observed_status[0] == status.ERROR


def manual_moveable_config():
    config = analog_moveable_config()
    config["mapping"] = {"14 Hz": 14, "28 Hz": 28}
    return config


def create_analog_pair(device_harness, fake_backend, *, name):
    """Create daemon+poller analog moveables with common baseline backend state."""
    config = analog_moveable_config()
    fake_backend.values[config["readpv"]] = 28.0
    fake_backend.values[config["writepv"]] = 28.0
    fake_backend.units[config["readpv"]] = "mm"
    fake_backend.alarms[config["readpv"]] = (status.OK, "ok")
    daemon_device, _poller_device = device_harness.create_pair(
        EpicsAnalogMoveable,
        name=name,
        shared=config,
    )
    return config, daemon_device
