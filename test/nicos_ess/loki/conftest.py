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

from test.nicos_ess.test_devices.doubles import HarnessLinearAxis

from nicos_ess.loki.devices.beamstop import (
    LokiBeamstopController,
    LokiBeamstopXPositioner,
)
from nicos_ess.devices.mapped_controller import MappedController

def _create_master(daemon_device_harness, devcls, /, *args, **kwargs):
    """Create devices in master mode so doStart/doStatus logic is exercised."""
    return daemon_device_harness.create_master(devcls, *args, **kwargs)

@pytest.fixture
def loki_beamstop_setup(daemon_device_harness):
    axis_x = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="axis_x",
        abslimits=(0.0, 100.0),
        precision=0.1,
        initial_value=5.0,
    )
    axis_y = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="axis_y",
        abslimits=(0.0, 100.0),
        precision=0.1,
        initial_value=5.0,
    )
    axis_1 = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="axis_1",
        abslimits=(0.0, 100.0),
        precision=0.1,
        initial_value=5.0,
    )
    axis_2 = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="axis_2",
        abslimits=(0.0, 100.0),
        precision=0.1,
        initial_value=5.0,
    )
    axis_3 = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="axis_3",
        abslimits=(0.0, 100.0),
        precision=0.1,
        initial_value=5.0,
    )
    axis_4 = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="axis_4",
        abslimits=(0.0, 100.0),
        precision=0.1,
        initial_value=5.0,
    )
    axis_5 = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="axis_5",
        abslimits=(0.0, 100.0),
        precision=0.1,
        initial_value=5.0,
    )
    positioner_x = _create_master(
        daemon_device_harness,
        LokiBeamstopXPositioner,
        name="positioner_x",
        controlled_device="axis_x",
        mapping={
            "Parked": 0,
            "Xpos BS1": 5,
            "Xpos BS2": 10,
            "Xpos BS3": 15,
            "Xpos BS4": 20,
            "Xpos BS5": 25,
        },
    )
    positioner_y = _create_master(
        daemon_device_harness,
        MappedController,
        name="positioner_y",
        controlled_device="axis_y",
        mapping={"In beam": 0},
    )
    positioner_1 = _create_master(
        daemon_device_harness,
        MappedController,
        name="positioner_1",
        controlled_device="axis_1",
        mapping={"Parked": 15, "Intermediate": 12, "In beam": 0},
    )
    positioner_2 = _create_master(
        daemon_device_harness,
        MappedController,
        name="positioner_2",
        controlled_device="axis_2",
        mapping={"Parked": 15, "Intermediate": 12, "In beam": 0},
    )
    positioner_3 = _create_master(
        daemon_device_harness,
        MappedController,
        name="positioner_3",
        controlled_device="axis_3",
        mapping={"Parked": 15, "Intermediate": 12, "In beam": 0},
    )
    positioner_4 = _create_master(
        daemon_device_harness,
        MappedController,
        name="positioner_4",
        controlled_device="axis_4",
        mapping={"Parked": 15, "Intermediate": 12, "In beam": 0},
    )
    positioner_5 = _create_master(
        daemon_device_harness,
        MappedController,
        name="positioner_5",
        controlled_device="axis_5",
        mapping={"Parked": 15, "Intermediate": 12, "In beam": 0},
    )
    controller = _create_master(
        daemon_device_harness,
        LokiBeamstopController,
        bsx_positioner="positioner_x",
        bsy_positioner="positioner_y",
        bs1_positioner="positioner_1",
        bs2_positioner="positioner_2",
        bs3_positioner="positioner_3",
        bs4_positioner="positioner_4",
        bs5_positioner="positioner_5",
    )
    devices = {
        "axis_x": axis_x,
        "axis_y": axis_y,
        "axis_1": axis_1,
        "axis_2": axis_2,
        "axis_3": axis_3,
        "axis_4": axis_4,
        "axis_5": axis_5,
        "positioner_x": positioner_x,
        "positioner_y": positioner_y,
        "positioner_1": positioner_1,
        "positioner_2": positioner_2,
        "positioner_3": positioner_3,
        "positioner_4": positioner_4,
        "positioner_5": positioner_5,
        "controller": controller,
    }
    return devices
