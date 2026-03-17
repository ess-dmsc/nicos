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
from nicos.core.errors import MoveError, PositionError

from test.nicos_ess.test_devices.epics_motor.helpers import (
    create_motor,
    create_motor_pair,
    pv,
)


class TestEpicsMotorCommandsAndMotion:
    def test_motor_can_move_when_miss_is_set(self, device_harness, fake_backend):
        dev = create_motor(device_harness)
        fake_backend.emit_update(pv(".MISS"), value=1)

        dev.move(5.0)
        assert fake_backend.values[pv(".VAL")] == 5.0

    @pytest.mark.parametrize(
        "rbv,target,deadband,movn,expected",
        [
            pytest.param(2.0, 3.0, 0.1, 0, False, id="outside_deadband_not_completed"),
            pytest.param(3.0, 3.0, 0.1, 1, False, id="moving_not_completed"),
            pytest.param(
                3.05, 3.0, 0.1, 0, True, id="inside_deadband_and_not_moving_completed"
            ),
        ],
    )
    def test_motor_iscompleted_uses_deadband_and_movn(
        self, device_harness, fake_backend, rbv, target, deadband, movn, expected
    ):
        fake_backend.values[pv(".RBV")] = rbv
        fake_backend.values[pv(".VAL")] = target
        fake_backend.values[pv(".RDBD")] = deadband
        fake_backend.values[pv(".MOVN")] = movn
        dev = create_motor(device_harness)

        assert dev.isCompleted() is expected

    def test_motor_start_does_not_write_target_when_within_precision(
        self, device_harness, fake_backend
    ):
        fake_backend.values[pv(".RBV")] = 2.5
        fake_backend.values[pv(".RDBD")] = 0.2
        dev = create_motor(device_harness)

        before = len(fake_backend.put_calls)
        dev.start(2.6)

        assert len(fake_backend.put_calls) == before

    def test_motor_start_writes_target_when_outside_precision(
        self, device_harness, fake_backend
    ):
        fake_backend.values[pv(".RBV")] = 2.5
        fake_backend.values[pv(".RDBD")] = 0.05
        dev = create_motor(device_harness)

        dev.start(2.7)

        assert fake_backend.values[pv(".VAL")] == 2.7

    @pytest.mark.parametrize(
        "movn,dmov",
        [
            pytest.param(1, 1, id="movn_is_one"),
            pytest.param(0, 0, id="dmov_is_zero"),
        ],
    )
    def test_motor_writeoffset_fails_while_motor_is_moving(
        self, device_harness, fake_backend, movn, dmov
    ):
        fake_backend.values[pv(".MOVN")] = movn
        fake_backend.values[pv(".DMOV")] = dmov
        dev = create_motor(device_harness)

        with pytest.raises(RuntimeError):
            device_harness.run_daemon(dev.doWriteOffset, 5.0)

    @pytest.mark.parametrize(
        "errorbit,expected_resetvalue",
        [
            pytest.param(0, 0, id="no_error_no_reset"),
            pytest.param(1, 1, id="error_triggers_reset"),
        ],
    )
    def test_motor_reset_writes_reseterror_only_when_error_bit_is_set(
        self, device_harness, fake_backend, errorbit, expected_resetvalue
    ):
        fake_backend.values[pv("-Err")] = errorbit
        dev = create_motor(device_harness)

        device_harness.run_daemon(dev.doReset)

        assert fake_backend.values[pv("-ErrRst")] == expected_resetvalue

    @pytest.mark.parametrize(
        "has_errorbit,has_reseterror",
        [
            pytest.param(False, True, id="missing_errorbit_support"),
            pytest.param(True, False, id="missing_reseterror_support"),
        ],
    )
    def test_motor_reset_is_noop_when_reset_support_is_disabled(
        self, device_harness, fake_backend, has_errorbit, has_reseterror
    ):
        fake_backend.values[pv("-Err")] = 1
        dev = create_motor(
            device_harness,
            has_errorbit=has_errorbit,
            has_reseterror=has_reseterror,
        )

        device_harness.run_daemon(dev.doReset)

        assert fake_backend.values[pv("-ErrRst")] == 0

    @pytest.mark.parametrize(
        "rbv_alarm,pv_updates,expected_exception",
        [
            pytest.param(
                None,
                {".MISS": 1},
                PositionError,
                id="notreached_raises_positionerror",
            ),
            pytest.param(
                (status.ERROR, "record alarm"),
                {},
                MoveError,
                id="error_raises_moveerror",
            ),
            pytest.param(
                None,
                {"-MsgTxt": "invalid issue", "-MsgTxt.SEVR": 3},
                MoveError,
                id="unknown_raises_moveerror",
            ),
        ],
    )
    def test_motor_wait_raises_for_error_states(
        self,
        device_harness,
        fake_backend,
        rbv_alarm,
        pv_updates,
        expected_exception,
    ):
        start_pos = 2.5
        target = 3.5
        fake_backend.values[pv(".RBV")] = start_pos
        fake_backend.values[pv(".VAL")] = start_pos
        fake_backend.values[pv(".MOVN")] = 0
        fake_backend.values[pv(".DMOV")] = 1
        if rbv_alarm is not None:
            fake_backend.alarms[pv(".RBV")] = rbv_alarm
        for suffix, value in pv_updates.items():
            fake_backend.values[pv(suffix)] = value
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)

        device_harness.run_daemon(daemon_device.start, target)
        fake_backend.values[pv(".RBV")] = target
        fake_backend.values[pv(".VAL")] = target

        with pytest.raises(expected_exception):
            device_harness.run_daemon(daemon_device.wait)

    def test_motor_wait_returns_current_value_when_move_is_completed_and_reached(
        self, device_harness, fake_backend
    ):
        start_pos = 2.5
        target = 3.5
        fake_backend.values[pv(".RBV")] = start_pos
        fake_backend.values[pv(".VAL")] = start_pos
        fake_backend.values[pv(".MOVN")] = 0
        fake_backend.values[pv(".DMOV")] = 1
        fake_backend.values[pv(".MISS")] = 0
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)

        device_harness.run_daemon(daemon_device.start, target)
        fake_backend.values[pv(".RBV")] = target
        fake_backend.values[pv(".VAL")] = target

        assert device_harness.run_daemon(daemon_device.wait) == target
