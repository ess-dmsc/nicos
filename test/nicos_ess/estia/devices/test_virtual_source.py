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

"""Harness tests for ESTIA virtual source devices."""

import pytest

from nicos.core import Moveable, Param, status, tupleof

from nicos_ess.estia.devices.virtual_source import VSCalculator, VirtualSlit


class HarnessVirtualSourceSlit(Moveable):
    """Minimal slit-blades double for `VirtualSlit` and `VSCalculator` tests.

    `virtual_source.py` reaches into the attached slit with:
    - `.start(...)`
    - `.isAllowed(...)`
    - `.status(...)`
    - `._doReadPositions(...)`
    - `.opmode` (including `_setROParam("opmode", ...)` sync paths)

    Keep this double tiny and extend only when a new behavior test needs more.
    """

    parameters = {
        "initial_positions": Param(
            "Initial blade positions: (-left, +right, -bottom, +top)",
            type=tupleof(float, float, float, float),
            default=(-1.0, 1.0, -0.5, 0.5),
            mandatory=False,
            userparam=False,
        ),
        "opmode": Param(
            "Current slit mode; synced by virtual source devices in read paths.",
            type=str,
            default="4blades",
            mandatory=False,
            userparam=False,
        ),
    }
    valuetype = tupleof(float, float, float, float)

    def doInit(self, mode):
        del mode
        self._positions = [float(v) for v in self.initial_positions]

    def _doReadPositions(self, maxage=0):
        del maxage
        return list(self._positions)

    def doRead(self, maxage=0):
        return self._doReadPositions(maxage)

    def doStart(self, target):
        self._positions = [float(v) for v in target]

    def doIsAllowed(self, target):
        del target
        return True, ""

    def doStatus(self, maxage=0):
        del maxage
        return status.OK, "harness double"


class HarnessVirtualSourceRotation(Moveable):
    """Minimal rotation-stage double used as the attached `rot` device."""

    parameters = {
        "initial_angle": Param(
            "Initial angle in degrees.",
            type=float,
            default=5.0,
            mandatory=False,
            userparam=False,
        ),
    }
    valuetype = float

    def doInit(self, mode):
        del mode
        self._angle = float(self.initial_angle)

    def doRead(self, maxage=0):
        del maxage
        return self._angle

    def doStart(self, target):
        self._angle = float(target)

    def doIsAllowed(self, target):
        del target
        return True, ""

    def doStatus(self, maxage=0):
        del maxage
        return status.OK, "harness double"


@pytest.fixture
def virtual_source_attached_device_names(device_harness):
    """Create attached-device doubles for both harness roles.

    Pattern for attached-device tests:
    1. create doubles first with `device_harness.create_pair(...)`
    2. pass double names into the device under test config (`slit` / `rot`)
    3. use `device_harness.get_device(role, name)` for role-specific checks
    """

    slit_name = "virtual_source_slit_double"
    rot_name = "virtual_source_rot_double"

    # These create one device in daemon and one in poller with identical config.
    device_harness.create_pair(
        HarnessVirtualSourceSlit,
        name=slit_name,
        shared={"opmode": "4blades"},
    )
    device_harness.create_pair(
        HarnessVirtualSourceRotation,
        name=rot_name,
        shared={"initial_angle": 7.5},
    )

    return {"slit": slit_name, "rot": rot_name}


class TestVirtualSource:
    def test_virtual_slit_initializes_with_harness_doubles(
        self, device_harness, virtual_source_attached_device_names
    ):
        """Smoke-test constructor wiring only (no motion/readout assertions)."""
        daemon_device, poller_device = device_harness.create_pair(
            VirtualSlit,
            name="virtual_source_slit",
            shared={
                "slit": virtual_source_attached_device_names["slit"],
                "rot": virtual_source_attached_device_names["rot"],
                "opmode": "4blades",
            },
        )

        assert daemon_device is not None
        assert poller_device is not None

        # Verify role-local attachment resolution.
        assert daemon_device._adevs["slit"] is device_harness.get_device(
            "daemon", virtual_source_attached_device_names["slit"]
        )
        assert daemon_device._adevs["rot"] is device_harness.get_device(
            "daemon", virtual_source_attached_device_names["rot"]
        )
        assert poller_device._adevs["slit"] is device_harness.get_device(
            "poller", virtual_source_attached_device_names["slit"]
        )
        assert poller_device._adevs["rot"] is device_harness.get_device(
            "poller", virtual_source_attached_device_names["rot"]
        )

    def test_vs_calculator_initializes_with_harness_doubles(
        self, device_harness, virtual_source_attached_device_names
    ):
        """Smoke-test constructor wiring for calculator helper device only."""
        daemon_device, poller_device = device_harness.create_pair(
            VSCalculator,
            name="virtual_source_calculator",
            shared={
                "slit": virtual_source_attached_device_names["slit"],
                "rot": virtual_source_attached_device_names["rot"],
                "opmode": "4blades",
            },
        )

        assert daemon_device is not None
        assert poller_device is not None
        assert daemon_device._adevs["slit"] is device_harness.get_device(
            "daemon", virtual_source_attached_device_names["slit"]
        )
        assert daemon_device._adevs["rot"] is device_harness.get_device(
            "daemon", virtual_source_attached_device_names["rot"]
        )
        assert poller_device._adevs["slit"] is device_harness.get_device(
            "poller", virtual_source_attached_device_names["slit"]
        )
        assert poller_device._adevs["rot"] is device_harness.get_device(
            "poller", virtual_source_attached_device_names["rot"]
        )

