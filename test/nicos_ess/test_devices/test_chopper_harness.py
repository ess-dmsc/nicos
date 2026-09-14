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
from nicos_ess.devices.epics.pva import EpicsMappedReadable, epics_common
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
        epics_common, "create_wrapper", lambda timeout, use_pva: backend
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
        shared={"mapping": {"0": 0, "14": 14}},
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
            "mapping": {"0": 0.0, "14": 14.0},
            "monitor": True,
            "pva": True,
        },
    )


@pytest.fixture
def attached_new_chopper_devices(device_harness, fake_backend):
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
        HarnessReadable,
        name="ess_chic_conn",
        shared={"initial": "Connected"},
    )

    fake_backend.values["SIM:CHOP:SPD.RBV"] = 14.0
    fake_backend.values["SIM:CHOP:SPD.VAL"] = 14.0
    fake_backend.values["SIM:CHOP:InPhase_R"] = "Not in phase"
    fake_backend.value_choices["SIM:CHOP:InPhase_R"] = [
        "Not in phase",
        "In phase",
    ]
    device_harness.create_pair(
        EpicsMappedReadable,
        name="ess_speed_in_phase",
        shared={
            "readpv": "SIM:CHOP:InPhase_R",
            "monitor": True,
            "pva": True,
        },
    )
    device_harness.create_pair(
        chopper_mod.EssChopperSpeed,
        name="ess_speed",
        shared={
            "readpv": "SIM:CHOP:SPD.RBV",
            "writepv": "SIM:CHOP:SPD.VAL",
            "mapping": {"0": 0.0, "14": 14.0},
            "monitor": True,
            "pva": True,
            "state": "ess_state",
            "in_phase": "ess_speed_in_phase",
        },
    )


@pytest.fixture
def chopper_speed_devices(device_harness, fake_backend):
    device_harness.create_pair(
        HarnessReadable,
        name="ess_state",
        shared={"initial": "Ready"},
    )

    fake_backend.values["SIM:CHOP:InPhase_R"] = "Not in phase"
    fake_backend.value_choices["SIM:CHOP:InPhase_R"] = [
        "Not in phase",
        "In phase",
    ]
    device_harness.create_pair(
        EpicsMappedReadable,
        name="ess_in_phase",
        shared={
            "readpv": "SIM:CHOP:InPhase_R",
            "monitor": True,
            "pva": True,
        },
    )


class TestChopperAlarmsHarness:
    def _create_pair(self, device_harness, devcls, name):
        return device_harness.create_pair(
            devcls,
            name=name,
            shared={
                "pv_root": "SIM:CHOP:",
                "monitor": True,
                "pva": True,
            },
        )

    def test_initializes(self, device_harness, fake_backend):
        del fake_backend
        daemon_device, poller_device = self._create_pair(
            device_harness, chopper_mod.ChopperAlarms, "chopper_alarms"
        )

        assert daemon_device is not None
        assert poller_device is not None

    def test_status_only_device_publishes_blank_value(
        self, device_harness, fake_backend
    ):
        del fake_backend
        daemon_device, _poller_device = self._create_pair(
            device_harness, chopper_mod.ChopperAlarms, "chopper_alarms"
        )

        assert daemon_device._cache.get(daemon_device, "value") == ""

    def test_alarm_update_is_reflected_in_status(self, device_harness, fake_backend):
        daemon_device, _poller_device = self._create_pair(
            device_harness, chopper_mod.ChopperAlarms, "chopper_alarms"
        )

        assert daemon_device.status()[0] == status.OK

        fake_backend.emit_update(
            "SIM:CHOP:HW_Alrm",
            value=1,
            severity=status.ERROR,
            message="hardware broken",
        )

        assert daemon_device.status() == (status.ERROR, "hardware alarm")

    def test_new_initializes(self, device_harness, fake_backend):
        del fake_backend
        daemon_device, poller_device = self._create_pair(
            device_harness, chopper_mod.NewChopperAlarms, "new_chopper_alarms"
        )

        assert daemon_device is not None
        assert poller_device is not None


class TestEssChopperControllerHarness:
    def test_initializes(self, device_harness, fake_backend, attached_chopper_devices):
        del fake_backend, attached_chopper_devices
        daemon_device, poller_device = device_harness.create_pair(
            chopper_mod.EssChopperController,
            name="ess_chopper",
            shared={
                "state": "ess_state",
                "command": "ess_command",
                "speed": "ess_speed",
                "chic_conn": "ess_chic_conn",
                "mapping": {"stop": "stop", "start": "start"},
            },
        )

        assert daemon_device is not None
        assert poller_device is not None


class TestNewEssChopperControllerHarness:
    def test_initializes(
        self, device_harness, fake_backend, attached_new_chopper_devices
    ):
        del fake_backend, attached_new_chopper_devices
        daemon_device, poller_device = device_harness.create_pair(
            chopper_mod.NewEssChopperController,
            name="ess_chopper",
            shared={
                "state": "ess_state",
                "command": "ess_command",
                "speed": "ess_speed",
                "chic_conn": "ess_chic_conn",
                "mapping": {"stop": "stop", "start": "start"},
            },
        )

        assert daemon_device is not None
        assert poller_device is not None


class TestEssChopperSpeed:
    def _create_pair(self, device_harness):
        return device_harness.create_pair(
            chopper_mod.EssChopperSpeed,
            name="ess_chopper_speed",
            shared={
                "readpv": "SIM:ODIN:SPD.RBV",
                "writepv": "SIM:ODIN:SPD.VAL",
                "mapping": {"0": 0.0, "14": 14.0},
                "monitor": True,
                "pva": True,
                "state": "ess_state",
                "in_phase": "ess_in_phase",
            },
        )

    def test_initializes(self, device_harness, fake_backend, chopper_speed_devices):
        del fake_backend, chopper_speed_devices
        daemon_device, poller_device = self._create_pair(device_harness)

        assert daemon_device is not None
        assert poller_device is not None

    def test_completes_by_state_when_target_is_zero(
        self, device_harness, fake_backend, chopper_speed_devices
    ):
        del fake_backend, chopper_speed_devices
        daemon_device, _poller_device = self._create_pair(device_harness)

        daemon_device._setROParam("target", daemon_device.TARGET_ZERO)
        assert daemon_device.doIsCompleted() is True

    def test_not_completed_by_state_when_not_ready(self, device_harness, fake_backend):
        device_harness.create_pair(
            HarnessReadable,
            name="ess_state",
            shared={"initial": "Moving"},
        )

        fake_backend.values["SIM:CHOP:InPhase_R"] = "Not in phase"
        fake_backend.value_choices["SIM:CHOP:InPhase_R"] = [
            "Not in phase",
            "In phase",
        ]
        device_harness.create_pair(
            EpicsMappedReadable,
            name="ess_in_phase",
            shared={
                "readpv": "SIM:CHOP:InPhase_R",
                "monitor": True,
                "pva": True,
            },
        )

        daemon_device, _poller_device = self._create_pair(device_harness)

        daemon_device._setROParam("target", daemon_device.TARGET_ZERO)
        assert daemon_device.doIsCompleted() is False

    def test_completes_on_inphase_rising_edge_when_target_nonzero(
        self, device_harness, fake_backend, chopper_speed_devices
    ):
        del chopper_speed_devices
        daemon_device, _poller_device = self._create_pair(device_harness)

        daemon_device._setROParam("target", "14")

        assert daemon_device.doIsCompleted() is False
        assert daemon_device._previous_inphase is False

        fake_backend.emit_update("SIM:CHOP:InPhase_R", value="In phase")

        assert daemon_device.doIsCompleted() is True
        assert daemon_device._previous_inphase is True

        assert daemon_device.doIsCompleted() is False
