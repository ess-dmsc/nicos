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
    """
    Postulates:

        1) Commanding chopper to "Stop" or setting target to 0 Hz has the same effect

        2) "Stop" command also stops IOC chopper statistics that determines if
                the chopper is phased or not

        3) When chopper stops, state pv changes from "Rotating" to "Ready"
    """

    def _create_pair(self, device_harness):
        return device_harness.create_pair(
            chopper_mod.EssChopperSpeed,
            name="ess_chopper_speed",
            shared={
                "readpv": "SIM:ODIN:SPD.RBV",
                "writepv": "SIM:ODIN:SPD.VAL",
                "mapping": {"0": 0.0, "7": 7.0, "14": 14.0},
                "monitor": True,
                "pva": True,
                "state": "ess_state",
                "in_phase": "ess_in_phase",
            },
        )

    def ready_state_zero_target(delay_calls, state_device, fake_backend, **_):
        """
        Given the postulates (see `TestEssChopperSpeed` class docstring),
        doIsComplete must check on state pv transition from "Rotating" to
        "Ready" to determine whether the movement reached the steady state,
        not in_phase attached device, on this specific condition of stopping
        the chopper. Therefore, this test case will cover that situation.
        """
        if delay_calls["count"] == 1:
            fake_backend.emit_update("SIM:ODIN:SPD.RBV", value=0)
            state_device._cache.put(state_device.name, "value", "Ready")
        if delay_calls["count"] > 2:
            raise RuntimeError(
                "test guard: doIsCompleted did not catch the Rotating to Ready transition"
            )

    def non_ready_state_zero_target(delay_calls, state_device, fake_backend, **_):
        """
        Two conditions shall be met for the chopper to be considered at rest
        with zero angular speed, this test will force a state where one of the conditions
        is not met when stopping, the non Ready state. `maw` must continue waiting
        in this case.
        """
        if delay_calls["count"] == 1:
            fake_backend.emit_update("SIM:ODIN:SPD.RBV", value=0)
            state_device._cache.put(state_device.name, "value", "Comms not ok")

        if delay_calls["count"] == 2:
            # This call is here only to exit the maw without exceptions.
            #  In other words, it forces test exit by setting the exact
            #  parameters for maw to quit.
            #
            #  I appreciate if someone find a better way of doing it.
            state_device._cache.put(state_device.name, "value", "Ready")

        if delay_calls["count"] > 3:
            raise RuntimeError(
                "test guard: doIsCompleted did not catch the Rotating to Ready transition"
            )

    def ready_state_non_zero_target(
        delay_calls, state_device, fake_backend, speed_device, **_
    ):
        """
        Two conditions must be met for the chopper to be considered at rest
        with zero angular speed, this test will force a state where one of the conditions
        is not met when stopping, the non zero target. `maw` must continue waiting
        in this case.
        """
        if delay_calls["count"] == 1:
            state_device._cache.put(state_device.name, "value", "Ready")

        if delay_calls["count"] == 2:
            # This call is here only to exit the maw without exceptions.
            #  In other words, it forces test exit by setting the exact
            #  parameters for maw to quit.
            #
            #  I appreciate if someone find a better way of doing it.
            fake_backend.emit_update("SIM:ODIN:SPD.RBV", value=7)
            state_device._cache.put(speed_device.name, "target", "0")

        if delay_calls["count"] > 3:
            raise RuntimeError(
                "test guard: doIsCompleted did not catch the Rotating to Ready transition"
            )

    def in_phase_from_zero_speed(delay_calls, state_device, fake_backend, **_):
        """
        This case simulates the chopper start spinning from zero speed to the target
        speed (here 14 Hz) steady state. Thus, firstly, a transition from Ready to
        Rotating happens when the chopper start accelerating, then it reaches the
        target speed but not yet steady, i.e. the angular speed is still flickering.
        Finally, the in phase flag indicates that the chopper flickering standard
        deviation is below a set threshold in EPICS, considered steady state. Only
        after this last stage we can consider maw complete.
        """
        if delay_calls["count"] == 1:
            state_device._cache.put(state_device.name, "value", "Rotating")
            fake_backend.emit_update("SIM:ODIN:SPD.RBV", value=14)

        if delay_calls["count"] == 2:
            fake_backend.emit_update("SIM:CHOP:InPhase_R", value=1)

        if delay_calls["count"] > 3:
            raise RuntimeError(
                "test guard: doIsCompleted did not catch the in phase transition"
            )

    def in_phase_from_non_zero_speed_injection(
        delay_calls, state_device, fake_backend, **_
    ):
        """
        Similar to `in_phase_from_zero_speed_injection` but starts from non zero
        speed
        """
        if delay_calls["count"] == 1:
            state_device._cache.put(state_device.name, "value", "Rotating")
            fake_backend.emit_update("SIM:ODIN:SPD.RBV", value=14)

        if delay_calls["count"] == 2:
            fake_backend.emit_update("SIM:CHOP:InPhase_R", value=1)

        if delay_calls["count"] > 3:
            raise RuntimeError(
                "test guard: doIsCompleted did not catch the in phase transition"
            )

    def _maw_with_state_flip_during_wait(
        self,
        expected_value,
        speed_device,
        state_device,
        injection,
        fake_backend,
        device_harness,
    ):
        """
        Replaces NICOS' session.delay so `injection` can alter device state
        while the maw command is waiting.
        """
        from nicos import session as active_session

        original_delay = active_session.delay
        delay_calls = {"count": 0}

        def controlled_delay(seconds):
            delay_calls["count"] += 1
            injection(
                delay_calls=delay_calls,
                state_device=state_device,
                fake_backend=fake_backend,
                speed_device=speed_device,
            )
            return original_delay(seconds)

        active_session.delay = controlled_delay
        try:
            return speed_device.maw(str(expected_value)), delay_calls["count"]
        finally:
            active_session.delay = original_delay

    @pytest.mark.parametrize(
        "injection, initial_state, initial_speed, expected_value, expected_delay_calls",
        [
            (ready_state_zero_target, "Rotating", 14, 0, 1),
            (non_ready_state_zero_target, "Rotating", 14, 0, 2),
            (ready_state_non_zero_target, "Rotating", 14, 7, 2),
            (in_phase_from_zero_speed, "Ready", 0, 14, 2),
        ],
    )
    def test_maw(
        self,
        injection,
        initial_state,
        initial_speed,
        expected_value,
        expected_delay_calls,
        fake_backend,
        device_harness,
        chopper_speed_devices,
    ):
        """
        Parametrized move and wait tests that ensure that `doIsComplete` method
        works, under the postulates (see `TestEssChopperSpeed` class docstring)
        """

        # Set initial conditions
        speed_device, _ = self._create_pair(device_harness)
        fake_backend.emit_update("SIM:ODIN:SPD.RBV", value=initial_speed)
        state_device = device_harness.get_device(
            device_harness.POLLER_ROLE, "ess_state"
        )
        state_device._cache.put(state_device.name, "value", initial_state)

        value, delay_calls = device_harness.run(
            "daemon",
            self._maw_with_state_flip_during_wait,
            expected_value,
            speed_device,
            state_device,
            injection,
            fake_backend,
            device_harness,
        )

        assert delay_calls == expected_delay_calls
        assert value == expected_value
