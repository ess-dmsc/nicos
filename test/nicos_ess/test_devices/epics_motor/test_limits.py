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

from nicos.core.errors import ConfigurationError

from nicos_ess.devices.epics.pva.epics_devices import RecordInfo, RecordType
from nicos_ess.devices.epics.pva.motor import EpicsMotor

from test.nicos_ess.test_devices.epics_motor.helpers import (
    ASYMM_DIAL_LIMITS,
    DYNAMIC_HW_DIAL_LIMIT_CASES,
    INITIAL_DYNAMIC_HW_DIAL_LIMITS,
    OFFSET_CASES,
    TARGET_DIAL_USERLIMITS,
    WRITTEN_DYNAMIC_USER_DIAL_LIMITS,
    build_motor_cfg,
    create_monitored_motor_pair,
    create_motor_pair,
    pv,
    seed_limits,
    user_limits_from_dial_limits,
    userlimits_from_hw_window_and_limitoffsets,
)


class DerivedRecordFieldEpicsMotor(EpicsMotor):
    def doPreinit(self, mode):
        super().doPreinit(mode)
        self._record_fields["extra_field"] = RecordInfo("", ".XTR", RecordType.VALUE)


class TestEpicsMotorLegacyParity:
    def test_motor_adjust_updates_offset_for_redefined_position(
        self, device_harness, fake_backend
    ):
        fake_backend.values[pv(".RBV")] = 0.0
        fake_backend.values[pv(".DRBV")] = 0.0
        fake_backend.values[pv(".VAL")] = 0.0
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)

        device_harness.run_daemon(daemon_device.doAdjust, 0.0, 50.0)

        assert device_harness.run_daemon(daemon_device.doReadOffset) == 50.0
        assert fake_backend.values[pv(".VAL")] == 50.0

    def test_derived_motor_can_extend_record_field_mapping(self, device_harness):
        dev = device_harness.create(
            "daemon",
            DerivedRecordFieldEpicsMotor,
            name="motor",
            **build_motor_cfg(),
        )
        assert "extra_field" in dev._record_fields
        assert dev._record_fields["extra_field"].pv_suffix == ".XTR"


class TestEpicsMotorLimits:
    @pytest.mark.parametrize("offset", OFFSET_CASES)
    @pytest.mark.parametrize("direction", ["Pos", "Neg"], ids=["dir_pos", "dir_neg"])
    def test_motor_limits_are_read_for_all_direction_and_offset_cases_with_asymmetric_dial_limits(
        self, device_harness, fake_backend, direction, offset
    ):
        hw_umin, hw_umax = seed_limits(
            fake_backend,
            direction=direction,
            offset=offset,
            abs_dial_limits=ASYMM_DIAL_LIMITS,
        )
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)

        assert daemon_device.abslimits == ASYMM_DIAL_LIMITS
        assert daemon_device.hwuserlimits == (hw_umin, hw_umax)
        assert daemon_device.userlimits == (hw_umin, hw_umax)

    @pytest.mark.parametrize("offset", OFFSET_CASES)
    @pytest.mark.parametrize("direction", ["Pos", "Neg"], ids=["dir_pos", "dir_neg"])
    def test_motor_userlimits_are_written_for_all_direction_and_offset_cases_with_asymmetric_dial_limits(
        self, device_harness, fake_backend, direction, offset
    ):
        hw_umin, hw_umax = seed_limits(
            fake_backend,
            direction=direction,
            offset=offset,
            abs_dial_limits=ASYMM_DIAL_LIMITS,
        )
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)

        target_dial_min, target_dial_max = TARGET_DIAL_USERLIMITS
        target_umin, target_umax = user_limits_from_dial_limits(
            direction, offset, target_dial_min, target_dial_max
        )
        device_harness.run_daemon(
            daemon_device.doWriteUserlimits, (target_umin, target_umax)
        )

        expected_omin = target_umin - hw_umin
        expected_omax = target_umax - hw_umax
        assert daemon_device.abslimits == ASYMM_DIAL_LIMITS
        assert daemon_device.hwuserlimits == (hw_umin, hw_umax)
        assert daemon_device.limitoffsets == (expected_omin, expected_omax)
        assert daemon_device.userlimits == (target_umin, target_umax)

    @pytest.mark.parametrize(
        "new_hw_dial_limits, expected_range_change", DYNAMIC_HW_DIAL_LIMIT_CASES
    )
    @pytest.mark.parametrize("offset", OFFSET_CASES)
    @pytest.mark.parametrize("direction", ["Pos", "Neg"], ids=["dir_pos", "dir_neg"])
    def test_motor_userlimits_follow_dynamic_hardware_limit_updates_for_all_direction_and_offset_cases(
        self,
        device_harness,
        fake_backend,
        direction,
        offset,
        new_hw_dial_limits,
        expected_range_change,
    ):
        hw_umin, hw_umax = seed_limits(
            fake_backend,
            direction=direction,
            offset=offset,
            abs_dial_limits=ASYMM_DIAL_LIMITS,
            hw_dial_limits=INITIAL_DYNAMIC_HW_DIAL_LIMITS,
        )
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)

        user_dial_min, user_dial_max = WRITTEN_DYNAMIC_USER_DIAL_LIMITS
        written_umin, written_umax = user_limits_from_dial_limits(
            direction, offset, user_dial_min, user_dial_max
        )
        device_harness.run_daemon(
            daemon_device.doWriteUserlimits, (written_umin, written_umax)
        )

        expected_limitoffsets_before_update = (
            written_umin - hw_umin,
            written_umax - hw_umax,
        )
        before_userlimits = device_harness.run_daemon(daemon_device.doReadUserlimits)
        assert before_userlimits == pytest.approx((written_umin, written_umax))
        assert daemon_device.limitoffsets == pytest.approx(
            expected_limitoffsets_before_update
        )

        new_hw_dial_min, new_hw_dial_max = new_hw_dial_limits
        new_hw_umin, new_hw_umax = user_limits_from_dial_limits(
            direction, offset, new_hw_dial_min, new_hw_dial_max
        )
        fake_backend.emit_update(pv(".LLM"), value=new_hw_umin)
        fake_backend.emit_update(pv(".HLM"), value=new_hw_umax)
        fake_backend.values[pv(".LLM")] = 999.0
        fake_backend.values[pv(".HLM")] = -999.0

        expected_userlimits_after_update, expected_limitoffsets_after_update = (
            userlimits_from_hw_window_and_limitoffsets(
                new_hw_umin, new_hw_umax, expected_limitoffsets_before_update
            )
        )
        after_userlimits = device_harness.run_daemon(daemon_device.doReadUserlimits)
        assert daemon_device.abslimits == ASYMM_DIAL_LIMITS
        assert daemon_device.hwuserlimits == pytest.approx((new_hw_umin, new_hw_umax))
        assert after_userlimits == pytest.approx(expected_userlimits_after_update)
        assert daemon_device.limitoffsets == pytest.approx(
            expected_limitoffsets_after_update
        )

        before_width = before_userlimits[1] - before_userlimits[0]
        after_width = after_userlimits[1] - after_userlimits[0]
        if expected_range_change == "smaller":
            assert after_width < before_width
        elif expected_range_change == "larger":
            assert after_width > before_width
        else:
            assert after_userlimits == pytest.approx((new_hw_umin, new_hw_umax))
            assert daemon_device.limitoffsets == pytest.approx((0.0, 0.0))

    @pytest.mark.parametrize(
        "startup_moveable_limits_pending, expected_userlimits",
        [
            pytest.param(True, (-110.0, 140.0), id="startup_boundary_path"),
            pytest.param(False, (-90.0, 160.0), id="normal_userlimits_path"),
        ],
    )
    def test_motor_readuserlimits_startup_and_normal_paths(
        self,
        device_harness,
        fake_backend,
        startup_moveable_limits_pending,
        expected_userlimits,
    ):
        seed_limits(
            fake_backend,
            direction="Pos",
            offset=10.0,
            abs_dial_limits=ASYMM_DIAL_LIMITS,
        )
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)
        device_harness.run_daemon(
            lambda: setattr(
                daemon_device,
                "_startup_moveable_limits_pending",
                startup_moveable_limits_pending,
            )
        )

        assert (
            device_harness.run_daemon(daemon_device.doReadUserlimits)
            == expected_userlimits
        )
        assert daemon_device._startup_moveable_limits_pending is False

    @pytest.mark.parametrize(
        "pv_updates,error_match",
        [
            pytest.param(
                {".DLLM": 10.0, ".DHLM": -10.0},
                "invalid value for parameter abslimits",
                id="dial_limits_inverted",
            ),
            pytest.param(
                {".LLM": 10.0, ".HLM": -10.0},
                "hardware user lowlimit",
                id="hardware_limits_inverted",
            ),
            pytest.param(
                {".OFF": 10.0},
                "hardware userlimits",
                id="hardware_limits_inconsistent_with_offset",
            ),
        ],
    )
    def test_motor_limits_read_fails_for_invalid_epics_configuration(
        self, device_harness, fake_backend, pv_updates, error_match
    ):
        for suffix, value in pv_updates.items():
            fake_backend.values[pv(suffix)] = value

        with pytest.raises(ConfigurationError, match=error_match):
            create_motor_pair(device_harness, monitor=False)

    def test_motor_limits_read_accepts_hardware_limits_within_relative_tolerance(
        self, device_harness, fake_backend
    ):
        dial_min, dial_max = ASYMM_DIAL_LIMITS
        tol_min = abs(dial_min) * EpicsMotor.limit_rel_tolerance
        tol_max = abs(dial_max) * EpicsMotor.limit_rel_tolerance

        fake_backend.values[pv(".DIR")] = "Pos"
        fake_backend.values[pv(".OFF")] = 0.0
        fake_backend.values[pv(".DLLM")] = dial_min
        fake_backend.values[pv(".DHLM")] = dial_max
        fake_backend.values[pv(".LLM")] = dial_min - tol_min * 0.5
        fake_backend.values[pv(".HLM")] = dial_max + tol_max * 0.5

        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)

        assert daemon_device.hwuserlimits == pytest.approx(
            (dial_min - tol_min * 0.5, dial_max + tol_max * 0.5)
        )

    def test_motor_limits_read_rejects_hardware_limits_outside_relative_tolerance(
        self, device_harness, fake_backend
    ):
        dial_min, dial_max = ASYMM_DIAL_LIMITS
        tol_min = abs(dial_min) * EpicsMotor.limit_rel_tolerance

        fake_backend.values[pv(".DIR")] = "Pos"
        fake_backend.values[pv(".OFF")] = 0.0
        fake_backend.values[pv(".DLLM")] = dial_min
        fake_backend.values[pv(".DHLM")] = dial_max
        fake_backend.values[pv(".LLM")] = dial_min - tol_min * 2.0
        fake_backend.values[pv(".HLM")] = dial_max

        with pytest.raises(ConfigurationError, match="hardware userlimits"):
            create_motor_pair(device_harness, monitor=False)

    def test_motor_write_userlimits_accepts_boundaries_within_relative_tolerance(
        self, device_harness, fake_backend
    ):
        dial_min, dial_max = ASYMM_DIAL_LIMITS
        seed_limits(
            fake_backend,
            direction="Pos",
            offset=0.0,
            abs_dial_limits=ASYMM_DIAL_LIMITS,
        )
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)

        tol_min = abs(dial_min) * daemon_device.limit_rel_tolerance
        tol_max = abs(dial_max) * daemon_device.limit_rel_tolerance
        requested_limits = (dial_min - tol_min * 0.5, dial_max + tol_max * 0.5)

        device_harness.run_daemon(daemon_device.doWriteUserlimits, requested_limits)

        assert daemon_device.userlimits == pytest.approx(requested_limits)

    def test_motor_write_userlimits_rejects_boundaries_outside_relative_tolerance(
        self, device_harness, fake_backend
    ):
        dial_min, dial_max = ASYMM_DIAL_LIMITS
        seed_limits(
            fake_backend,
            direction="Pos",
            offset=0.0,
            abs_dial_limits=ASYMM_DIAL_LIMITS,
        )
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)

        tol_min = abs(dial_min) * daemon_device.limit_rel_tolerance
        requested_limits = (dial_min - tol_min * 2.0, dial_max)

        with pytest.raises(ConfigurationError, match="below absolute minimum"):
            device_harness.run_daemon(daemon_device.doWriteUserlimits, requested_limits)

    @pytest.mark.parametrize(
        "requested_limits",
        [
            pytest.param((10.0, -10.0), id="user_min_above_user_max"),
            pytest.param((-130.0, 100.0), id="below_abs_min"),
            pytest.param((-100.0, 130.0), id="above_abs_max"),
        ],
    )
    def test_motor_write_userlimits_rejects_invalid_ranges(
        self, device_harness, requested_limits
    ):
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)
        with pytest.raises(ConfigurationError):
            device_harness.run_daemon(daemon_device.doWriteUserlimits, requested_limits)
