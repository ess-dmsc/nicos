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
from nicos_ess.devices.epics import chopper as chopper_mod
from nicos_ess.devices.epics.chopper import (
    CHOPPER_CACHE_RAW_ERRORS_PARAM,
    CHOPPER_CACHE_VALUE_PARAM,
    CHOPPER_GUI_CHOPPER,
    CHOPPER_GUI_DELAY_ERRORS_KEY,
    CHOPPER_GUI_METADATA_FIELDS,
    CHOPPER_GUI_PARK_ANGLE_KEY,
    CHOPPER_GUI_SPEED_KEY,
    CHOPPER_GUI_TOTAL_DELAY_KEY,
)
from nicos_ess.devices.epics.pva import epics_devices
from nicos_ess.devices.epics.pva.epics_devices import EpicsManualMappedAnalogMoveable
from test.nicos_ess.test_devices.doubles import (
    FakeEpicsBackend,
    HarnessMappedMoveable,
    HarnessReadable,
)


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

    device_harness.create_pair(
        HarnessReadable,
        name="ess_state",
        shared={"initial": "stop"},
    )
    device_harness.create_pair(
        HarnessMappedMoveable,
        name="ess_command",
        shared={"mapping": {"stop": 0, "start": 1}},
    )
    device_harness.create_pair(
        HarnessMappedMoveable,
        name="ess_speed",
        shared={"mapping": {"0 Hz": 0, "14 Hz": 14}},
    )
    device_harness.create_pair(
        HarnessReadable,
        name="ess_total_delay",
        shared={"initial": "12.5"},
    )
    device_harness.create_pair(
        HarnessReadable,
        name="ess_park_angle",
        shared={"initial": "30.0"},
    )
    device_harness.create_pair(
        HarnessReadable,
        name="ess_delay_errors",
        shared={"initial": ""},
    )
    device_harness.create_pair(
        HarnessReadable,
        name="ess_chic_conn",
        shared={"initial": "Connected"},
    )
    device_harness.create_pair(
        EpicsManualMappedAnalogMoveable,
        name="odin_speed",
        shared={
            "readpv": "SIM:ODIN:SPD.RBV",
            "writepv": "SIM:ODIN:SPD.VAL",
            "mapping": {"0 Hz": 0.0, "14 Hz": 14.0},
            "monitor": True,
            "pva": True,
        },
    )
    device_harness.create_pair(
        HarnessReadable,
        name="odin_total_delay",
        shared={"initial": "25.0"},
    )
    device_harness.create_pair(
        HarnessReadable,
        name="odin_park_angle",
        shared={"initial": "137.795"},
    )
    device_harness.create_pair(
        HarnessReadable,
        name="odin_delay_errors",
        shared={"initial": ""},
    )
    device_harness.create_pair(
        HarnessReadable,
        name="odin_chic_conn",
        shared={"initial": "Connected"},
    )


def ess_chopper_config(**overrides):
    config = {
        "state": "ess_state",
        "command": "ess_command",
        "speed": "ess_speed",
        "total_delay": "ess_total_delay",
        "park_angle": "ess_park_angle",
        "chic_conn": "ess_chic_conn",
        "mapping": {"stop": "stop", "start": "start"},
        "slit_edges": [[0.0, 90.0]],
        "motor_position": "downstream",
        "tdc_resolver_position": 60.0,
        "park_open_angle": 30.0,
        "disk_delay": 1.5,
    }
    config.update(overrides)
    return config


def odin_chopper_config(**overrides):
    config = {
        "pv_root": "SIM:CHOP:",
        "speed": "odin_speed",
        "total_delay": "odin_total_delay",
        "park_angle": "odin_park_angle",
        "delay_errors": "odin_delay_errors",
        "chic_conn": "odin_chic_conn",
        "mapping": {
            "stop": "stop",
            "start": "start",
            "a_start": "a_start",
            "park": "park",
        },
        "monitor": True,
        "pva": True,
        "slit_edges": [[0.0, 46.71]],
        "motor_position": "downstream",
        "positive_speed_rotation_direction": "CW",
        "resolver_positive_direction": "CW",
        "parked_opening_index": 0,
        "tdc_resolver_position": 0.0,
        "park_open_angle": 137.795,
        "disk_delay": 0.0,
    }
    config.update(overrides)
    return config


class TestChopperAlarmsHarness:
    def test_initializes(self, device_harness, fake_backend):
        del fake_backend
        daemon_device, poller_device = device_harness.create_pair(
            chopper_mod.ChopperAlarms,
            name="chopper_alarms",
            shared={
                "pv_root": "SIM:CHOP:",
                "monitor": True,
                "pva": True,
            },
        )

        assert daemon_device is not None
        assert poller_device is not None


class TestEssChopperControllerHarness:
    def test_initializes(self, device_harness, fake_backend, attached_chopper_devices):
        del fake_backend, attached_chopper_devices
        daemon_device, poller_device = device_harness.create_pair(
            chopper_mod.EssChopperController,
            name="ess_chopper",
            shared=ess_chopper_config(),
        )

        assert daemon_device is not None
        assert poller_device is not None

    @pytest.mark.parametrize(
        "alarm_cls",
        [chopper_mod.ChopperAlarms, chopper_mod.ChopperAlarmsV2],
        ids=["legacy-alarms", "alarms-v2"],
    )
    def test_accepts_legacy_and_v2_alarm_devices(
        self, alarm_cls, device_harness, fake_backend, attached_chopper_devices
    ):
        del fake_backend, attached_chopper_devices
        device_harness.create_pair(
            alarm_cls,
            name="ess_alarms",
            shared={
                "pv_root": "SIM:CHOP:",
                "monitor": True,
                "pva": True,
            },
        )
        daemon_device, poller_device = device_harness.create_pair(
            chopper_mod.EssChopperController,
            name="ess_chopper",
            shared=ess_chopper_config(alarms="ess_alarms"),
        )

        assert daemon_device is not None
        assert poller_device is not None
        assert device_harness.run_daemon(daemon_device.status, 0) == (status.OK, "")

    def test_chopper_gui_info_uses_attached_device_names(
        self, device_harness, fake_backend, attached_chopper_devices
    ):
        del fake_backend, attached_chopper_devices
        daemon_device, _poller_device = device_harness.create_pair(
            chopper_mod.EssChopperController,
            name="ess_chopper",
            shared=ess_chopper_config(delay_errors="ess_delay_errors"),
        )

        info = device_harness.run_daemon(daemon_device.get_chopper_gui_info)

        assert info[CHOPPER_GUI_CHOPPER] == "ess_chopper"
        assert info[CHOPPER_GUI_SPEED_KEY] == (
            f"ess_speed/{CHOPPER_CACHE_VALUE_PARAM}"
        )
        assert info[CHOPPER_GUI_TOTAL_DELAY_KEY] == (
            f"ess_total_delay/{CHOPPER_CACHE_VALUE_PARAM}"
        )
        assert info[CHOPPER_GUI_PARK_ANGLE_KEY] == (
            f"ess_park_angle/{CHOPPER_CACHE_VALUE_PARAM}"
        )
        assert info[CHOPPER_GUI_DELAY_ERRORS_KEY] == (
            f"ess_delay_errors/{CHOPPER_CACHE_RAW_ERRORS_PARAM}"
        )
        for field in CHOPPER_GUI_METADATA_FIELDS:
            assert field in info

    def test_chopper_gui_info_allows_missing_delay_errors(
        self, device_harness, fake_backend, attached_chopper_devices
    ):
        del fake_backend, attached_chopper_devices
        daemon_device, _poller_device = device_harness.create_pair(
            chopper_mod.EssChopperController,
            name="ess_chopper",
            shared=ess_chopper_config(),
        )

        info = device_harness.run_daemon(daemon_device.get_chopper_gui_info)

        assert info[CHOPPER_GUI_DELAY_ERRORS_KEY] is None


class TestOdinChopperControllerHarness:
    def test_initializes(self, device_harness, fake_backend, attached_chopper_devices):
        del fake_backend, attached_chopper_devices
        daemon_device, poller_device = device_harness.create_pair(
            chopper_mod.OdinChopperController,
            name="odin_chopper",
            shared=odin_chopper_config(),
        )

        assert daemon_device is not None
        assert poller_device is not None

    def test_chopper_gui_info_uses_attached_device_names(
        self, device_harness, fake_backend, attached_chopper_devices
    ):
        del fake_backend, attached_chopper_devices
        daemon_device, _poller_device = device_harness.create_pair(
            chopper_mod.OdinChopperController,
            name="odin_chopper",
            shared=odin_chopper_config(),
        )

        info = device_harness.run_daemon(daemon_device.get_chopper_gui_info)

        assert info[CHOPPER_GUI_CHOPPER] == "odin_chopper"
        assert info[CHOPPER_GUI_SPEED_KEY] == (
            f"odin_speed/{CHOPPER_CACHE_VALUE_PARAM}"
        )
        assert info[CHOPPER_GUI_TOTAL_DELAY_KEY] == (
            f"odin_total_delay/{CHOPPER_CACHE_VALUE_PARAM}"
        )
        assert info[CHOPPER_GUI_PARK_ANGLE_KEY] == (
            f"odin_park_angle/{CHOPPER_CACHE_VALUE_PARAM}"
        )
        assert info[CHOPPER_GUI_DELAY_ERRORS_KEY] == (
            f"odin_delay_errors/{CHOPPER_CACHE_RAW_ERRORS_PARAM}"
        )
        for field in CHOPPER_GUI_METADATA_FIELDS:
            assert field in info
