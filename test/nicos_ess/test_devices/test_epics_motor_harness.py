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
from nicos.core.errors import ConfigurationError, MoveError, PositionError

from nicos_ess.devices.epics.pva import motor
from nicos_ess.devices.epics.pva.epics_devices import RecordInfo, RecordType
from nicos_ess.devices.epics.pva.motor import EpicsMotor

from test.nicos_ess.test_devices.doubles import patch_create_wrapper

MOTOR_PV = "SIM:M1"
ASYMM_DIAL_LIMITS = (-100.0, 150.0)
TARGET_DIAL_USERLIMITS = (-80.0, 120.0)
INITIAL_DYNAMIC_HW_DIAL_LIMITS = (-60.0, 120.0)
WRITTEN_DYNAMIC_USER_DIAL_LIMITS = (-40.0, 110.0)

OFFSET_CASES = [
    pytest.param(-200.0, id="large_negative_offset"),
    pytest.param(-10.0, id="small_negative_offset"),
    pytest.param(0.0, id="zero_offset"),
    pytest.param(10.0, id="small_positive_offset"),
    pytest.param(200.0, id="large_positive_offset"),
]

DYNAMIC_HW_DIAL_LIMIT_CASES = [
    pytest.param((-30.0, 70.0), "smaller", id="hardware_tightens"),
    pytest.param((-85.0, 140.0), "larger", id="hardware_widens"),
    pytest.param((10.0, 30.0), "fallback", id="hardware_becomes_very_tight"),
]


@pytest.fixture
def fake_backend(monkeypatch):
    return patch_create_wrapper(monkeypatch, motor)


def pv(suffix):
    return f"{MOTOR_PV}{suffix}"


def build_motor_cfg(**overrides):
    cfg = {
        "motorpv": MOTOR_PV,
        "has_powerauto": True,
        "has_msgtxt": True,
        "has_errorbit": True,
        "has_reseterror": True,
        "monitor_deadband": 0.1,
        "monitor": False,
    }
    cfg.update(overrides)
    return cfg


@pytest.fixture(autouse=True)
def default_motor_pvs(fake_backend):
    defaults = {
        ".RBV": 2.5,
        ".DRBV": 2.5,
        ".VAL": 2.5,
        ".STOP": 0,
        ".VELO": 1.0,
        ".OFF": 0.0,
        ".HLM": 120.0,
        ".LLM": -120.0,
        ".DHLM": 120.0,
        ".DLLM": -120.0,
        ".CNEN": 1,
        ".SET": 0,
        ".FOFF": 0,
        ".DIR": "Pos",
        ".EGU": "mm",
        ".HOMF": 0,
        ".HOMR": 0,
        ".RDBD": 0.1,
        ".DESC": "Test Motor",
        ".MDEL": 0.1,
        ".VMAX": 10.0,
        ".VBAS": 0.1,
        ".DMOV": 1,
        ".MOVN": 0,
        ".MISS": 0,
        ".STAT": 0,
        ".SEVR": 0,
        ".LVIO": 0,
        ".LLS": 0,
        ".HLS": 0,
        "-Err": 0,
        "-ErrRst": 0,
        "-PwrAuto": 1,
        "-MsgTxt": "",
        "-MsgTxt.SEVR": 0,
    }
    for suffix, value in defaults.items():
        fake_backend.values[pv(suffix)] = value


STATUS_CASES = [
    pytest.param(
        [(pv(".DMOV"), 0), (pv(".MOVN"), 1)],
        {},
        status.BUSY,
        "moving to",
        False,
        id="busy_from_dmov_movn",
    ),
    pytest.param(
        [(pv(".HOMF"), 1), (pv(".DMOV"), 0)],
        {},
        status.BUSY,
        "homing",
        False,
        id="homing",
    ),
    pytest.param(
        [(pv("-PwrAuto"), 1), (pv(".CNEN"), 0), (pv(".DMOV"), 1), (pv(".MOVN"), 0)],
        {},
        status.OK,
        "",
        True,
        id="powerauto_on_disabled_motor_is_ok",
    ),
    pytest.param(
        [(pv("-PwrAuto"), 0), (pv(".CNEN"), 0), (pv(".DMOV"), 1), (pv(".MOVN"), 0)],
        {},
        status.WARN,
        "motor is not enabled",
        False,
        id="disabled_drive",
    ),
    pytest.param(
        [(pv(".CNEN"), 0), (pv(".DMOV"), 1), (pv(".MOVN"), 0)],
        {"has_powerauto": False},
        status.WARN,
        "motor is not enabled",
        False,
        id="no_powerauto_and_disabled_drive",
    ),
    pytest.param(
        [(pv(".DMOV"), 1), (pv(".MOVN"), 0), (pv(".MISS"), 1)],
        {},
        status.NOTREACHED,
        "did not reach target",
        False,
        id="miss",
    ),
    pytest.param(
        [(pv(".DMOV"), 1), (pv(".MOVN"), 0), (pv(".LVIO"), 1)],
        {},
        status.WARN,
        "soft limit violation",
        False,
        id="softlimit",
    ),
    pytest.param(
        [(pv(".DMOV"), 1), (pv(".MOVN"), 0), (pv(".LLS"), 1)],
        {},
        status.WARN,
        "low limit switch",
        False,
        id="low_limit_switch",
    ),
    pytest.param(
        [(pv(".DMOV"), 1), (pv(".MOVN"), 0), (pv(".HLS"), 1)],
        {},
        status.WARN,
        "high limit switch",
        False,
        id="high_limit_switch",
    ),
]

STATUS_SEVERITY_AND_MESSAGE_PRECEDENCE_CASES = [
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [],
        status.OK,
        "",
        True,
        id="ok_status_returns_empty_message_even_when_msgtxt_has_text",
    ),
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [(pv(".LVIO"), 1)],
        status.WARN,
        "soft limit violation",
        False,
        id="softlimit_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [(pv(".LLS"), 1)],
        status.WARN,
        "low limit switch",
        False,
        id="low_limit_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [(pv(".HLS"), 1)],
        status.WARN,
        "high limit switch",
        False,
        id="high_limit_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [(pv(".MISS"), 1)],
        status.NOTREACHED,
        "did not reach target",
        False,
        id="miss_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [(pv(".DMOV"), 0), (pv(".MOVN"), 1)],
        status.BUSY,
        "moving to",
        False,
        id="moving_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [(pv("-PwrAuto"), 0), (pv(".CNEN"), 0)],
        status.WARN,
        "motor is not enabled",
        False,
        id="disabled_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.WARN, "record alarm"),
        0,
        "hello",
        [],
        status.WARN,
        "record alarm",
        False,
        id="record_alarm_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.OK, ""),
        1,
        "minor issue",
        [],
        status.WARN,
        "minor issue",
        False,
        id="msgtxt_minor_sets_warn_with_msgtxt_message",
    ),
    pytest.param(
        (status.OK, ""),
        2,
        "major issue",
        [],
        status.ERROR,
        "major issue",
        False,
        id="msgtxt_major_sets_error_with_msgtxt_message",
    ),
    pytest.param(
        (status.OK, ""),
        3,
        "invalid issue",
        [],
        status.UNKNOWN,
        "invalid issue",
        False,
        id="msgtxt_invalid_sets_unknown_with_msgtxt_message",
    ),
]


def create_motor(device_harness, **cfg_overrides):
    return device_harness.create(
        "daemon",
        EpicsMotor,
        name="motor",
        **build_motor_cfg(**cfg_overrides),
    )


def create_motor_pair(device_harness, monitor, **cfg_overrides):
    cfg = build_motor_cfg()
    cfg["monitor"] = monitor
    cfg.update(cfg_overrides)
    return device_harness.create_pair(EpicsMotor, name="motor", shared=cfg)


def create_monitored_motor_pair(device_harness, **cfg_overrides):
    return create_motor_pair(device_harness, monitor=True, **cfg_overrides)


def user_limits_from_dial_limits(direction, offset, dial_min, dial_max):
    if direction == "Pos":
        return dial_min + offset, dial_max + offset
    return -dial_max + offset, -dial_min + offset


def userlimits_from_hw_window_and_limitoffsets(hw_umin, hw_umax, limitoffsets):
    omin, omax = limitoffsets
    umin = hw_umin + omin
    umax = hw_umax + omax

    if umax < umin:
        return (hw_umin, hw_umax), (0.0, 0.0)

    umin = max(min(umin, hw_umax), hw_umin)
    umax = max(min(umax, hw_umax), hw_umin)
    return (umin, umax), (umin - hw_umin, umax - hw_umax)


def seed_limits(
    fake_backend,
    *,
    direction,
    offset,
    abs_dial_limits=ASYMM_DIAL_LIMITS,
    hw_dial_limits=None,
):
    dial_min, dial_max = abs_dial_limits
    hw_dial_limits = abs_dial_limits if hw_dial_limits is None else hw_dial_limits
    hw_dial_min, hw_dial_max = hw_dial_limits
    hw_umin, hw_umax = user_limits_from_dial_limits(
        direction, offset, hw_dial_min, hw_dial_max
    )
    fake_backend.values[pv(".DIR")] = direction
    fake_backend.values[pv(".OFF")] = offset
    fake_backend.values[pv(".DLLM")] = dial_min
    fake_backend.values[pv(".DHLM")] = dial_max
    fake_backend.values[pv(".LLM")] = hw_umin
    fake_backend.values[pv(".HLM")] = hw_umax
    return hw_umin, hw_umax


def changed_pv_value(value):
    if isinstance(value, (int, float)):
        return 0 if value else 1
    return value


def set_state_pvs(fake_backend, state_pvs):
    for key, value in state_pvs:
        fake_backend.values[key] = value


def assert_status_result(
    actual_status,
    actual_message,
    expected_status,
    expected_message,
    expect_empty_message,
):
    assert actual_status == expected_status
    if expect_empty_message:
        assert actual_message == ""
    else:
        assert expected_message in actual_message


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


class TestEpicsMotorStatus:
    @pytest.mark.parametrize(
        "state_pvs,cfg_overrides,expected_status,expected_message,expect_empty_message",
        STATUS_CASES,
    )
    def test_motor_status_from_direct_backend_state(
        self,
        device_harness,
        fake_backend,
        state_pvs,
        cfg_overrides,
        expected_status,
        expected_message,
        expect_empty_message,
    ):
        set_state_pvs(fake_backend, state_pvs)
        dev = create_motor(device_harness, **cfg_overrides)

        st, msg = dev.status(0)
        assert_status_result(
            st, msg, expected_status, expected_message, expect_empty_message
        )

    @pytest.mark.parametrize(
        "state_pvs,cfg_overrides,expected_status,expected_message,expect_empty_message",
        STATUS_CASES,
    )
    def test_motor_status_from_existing_epics_state_when_pair_is_created(
        self,
        device_harness,
        fake_backend,
        state_pvs,
        cfg_overrides,
        expected_status,
        expected_message,
        expect_empty_message,
    ):
        set_state_pvs(fake_backend, state_pvs)
        daemon_device, _poller_device = create_monitored_motor_pair(
            device_harness, **cfg_overrides
        )

        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert_status_result(
            st, msg, expected_status, expected_message, expect_empty_message
        )

    @pytest.mark.parametrize(
        "state_pvs,cfg_overrides,expected_status,expected_message,expect_empty_message",
        STATUS_CASES,
    )
    def test_motor_status_updates_while_pair_is_running_via_poller_callbacks(
        self,
        device_harness,
        fake_backend,
        state_pvs,
        cfg_overrides,
        expected_status,
        expected_message,
        expect_empty_message,
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(
            device_harness, **cfg_overrides
        )
        assert device_harness.run_daemon(daemon_device.status, 0)[0] == status.OK

        for key, value in state_pvs:
            fake_backend.emit_update(key, value=value)
        for key, value in state_pvs:
            fake_backend.values[key] = changed_pv_value(value)

        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert_status_result(
            st, msg, expected_status, expected_message, expect_empty_message
        )

    def test_motor_status_warns_immediately_when_only_cnen_changes_to_disabled(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)

        fake_backend.emit_update(pv("-PwrAuto"), value=0)
        fake_backend.emit_update(pv(".CNEN"), value=0)

        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert st == status.WARN
        assert "motor is not enabled" in msg

    def test_motor_status_clears_warning_immediately_when_only_cnen_changes_to_enabled(
        self, device_harness, fake_backend
    ):
        fake_backend.values[pv("-PwrAuto")] = 0
        fake_backend.values[pv(".CNEN")] = 0
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)
        assert device_harness.run_daemon(daemon_device.status, 0)[0] == status.WARN

        fake_backend.emit_update(pv(".CNEN"), value=1)

        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert st == status.OK
        assert msg == ""

    def test_motor_status_alarm_error_takes_precedence_over_motion_flags(
        self, device_harness, fake_backend
    ):
        fake_backend.values[pv(".DMOV")] = 0
        fake_backend.values[pv(".MOVN")] = 1
        fake_backend.alarms[pv(".RBV")] = (status.ERROR, "record alarm")
        dev = create_motor(device_harness, has_msgtxt=False)

        assert dev.status(0) == (status.ERROR, "record alarm")

    @pytest.mark.parametrize(
        "rbv_alarm,msgtxt_severity,msgtxt,state_pvs,expected_status,expected_message,expect_empty_message",
        STATUS_SEVERITY_AND_MESSAGE_PRECEDENCE_CASES,
    )
    def test_motor_status_selects_correct_severity_and_message_source(
        self,
        device_harness,
        fake_backend,
        rbv_alarm,
        msgtxt_severity,
        msgtxt,
        state_pvs,
        expected_status,
        expected_message,
        expect_empty_message,
    ):
        fake_backend.alarms[pv(".RBV")] = rbv_alarm
        fake_backend.values[pv("-MsgTxt")] = msgtxt
        fake_backend.values[pv("-MsgTxt.SEVR")] = msgtxt_severity
        set_state_pvs(fake_backend, state_pvs)
        dev = create_motor(device_harness, has_msgtxt=True)

        st, msg = dev.status(0)
        assert_status_result(
            st, msg, expected_status, expected_message, expect_empty_message
        )

    @pytest.mark.parametrize(
        "rbv_alarm,msgtxt_severity,msgtxt,state_pvs,expected_status,expected_message,expect_empty_message",
        STATUS_SEVERITY_AND_MESSAGE_PRECEDENCE_CASES,
    )
    def test_motor_status_updates_correct_severity_and_message_source(
        self,
        device_harness,
        fake_backend,
        rbv_alarm,
        msgtxt_severity,
        msgtxt,
        state_pvs,
        expected_status,
        expected_message,
        expect_empty_message,
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(
            device_harness, has_msgtxt=True
        )

        fake_backend.alarms[pv(".RBV")] = rbv_alarm
        fake_backend.values[pv("-MsgTxt")] = msgtxt
        fake_backend.values[pv("-MsgTxt.SEVR")] = msgtxt_severity
        set_state_pvs(fake_backend, state_pvs)

        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert_status_result(
            st, msg, expected_status, expected_message, expect_empty_message
        )

    def test_motor_status_from_existing_epics_alarm_state_when_pair_is_created(
        self, device_harness, fake_backend
    ):
        fake_backend.alarms[pv(".RBV")] = (status.ERROR, "record alarm")
        daemon_device, _poller_device = create_monitored_motor_pair(
            device_harness, has_msgtxt=False
        )

        assert device_harness.run_daemon(daemon_device.status, 0) == (
            status.ERROR,
            "record alarm",
        )

    def test_motor_status_updates_from_alarm_state_while_pair_is_running(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(
            device_harness, has_msgtxt=False
        )

        fake_backend.alarms[pv(".RBV")] = (status.ERROR, "record alarm")
        fake_backend.emit_update(pv(".DMOV"), value=1)
        fake_backend.values[pv(".DMOV")] = 0

        assert device_harness.run_daemon(daemon_device.status, 0) == (
            status.ERROR,
            "record alarm",
        )

    def test_motor_connection_loss_sets_communication_failure_status_in_monitor_mode(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)

        fake_backend.emit_connection(pv(".RBV"), False)

        assert device_harness.run_daemon(daemon_device.status, 0) == (
            status.ERROR,
            "communication failure",
        )


class TestEpicsMotorCacheAndReadPaths:
    def test_daemon_read_uses_poller_cached_rbv_update(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)

        fake_backend.emit_update(pv(".RBV"), value=9.5)
        fake_backend.values[pv(".RBV")] = 99.0

        assert device_harness.run_daemon(daemon_device.read, 0) == 9.5

    def test_daemon_iscompleted_uses_poller_cached_updates(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)

        fake_backend.emit_update(pv(".RBV"), value=3.0)
        fake_backend.emit_update(pv(".VAL"), value=3.0)
        fake_backend.emit_update(pv(".RDBD"), value=0.1)
        fake_backend.emit_update(pv(".MOVN"), value=1)
        assert device_harness.run_daemon(daemon_device.isCompleted) is False

        fake_backend.emit_update(pv(".MOVN"), value=0)
        assert device_harness.run_daemon(daemon_device.isCompleted) is True

    def test_daemon_read_uses_backend_directly_when_monitor_is_disabled(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)

        fake_backend.emit_update(pv(".RBV"), value=9.5)
        fake_backend.values[pv(".RBV")] = 99.0

        assert device_harness.run_daemon(daemon_device.read, 0) == 99.0

    def test_daemon_status_uses_backend_directly_when_monitor_is_disabled(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)

        fake_backend.emit_update(pv(".MISS"), value=1)
        fake_backend.values[pv(".MISS")] = 0

        assert device_harness.run_daemon(daemon_device.status, 0)[0] == status.OK


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
