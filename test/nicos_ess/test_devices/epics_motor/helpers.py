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

from nicos_ess.devices.epics.pva.motor import EpicsMotor

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


STATUS_CASES = [
    pytest.param(
        [(f"{MOTOR_PV}.DMOV", 0), (f"{MOTOR_PV}.MOVN", 1)],
        {},
        status.BUSY,
        "moving to",
        False,
        id="busy_from_dmov_movn",
    ),
    pytest.param(
        [(f"{MOTOR_PV}.HOMF", 1), (f"{MOTOR_PV}.DMOV", 0)],
        {},
        status.BUSY,
        "homing",
        False,
        id="homing",
    ),
    pytest.param(
        [
            (f"{MOTOR_PV}-PwrAuto", 1),
            (f"{MOTOR_PV}.CNEN", 0),
            (f"{MOTOR_PV}.DMOV", 1),
            (f"{MOTOR_PV}.MOVN", 0),
        ],
        {},
        status.OK,
        "",
        True,
        id="powerauto_on_disabled_motor_is_ok",
    ),
    pytest.param(
        [
            (f"{MOTOR_PV}-PwrAuto", 0),
            (f"{MOTOR_PV}.CNEN", 0),
            (f"{MOTOR_PV}.DMOV", 1),
            (f"{MOTOR_PV}.MOVN", 0),
        ],
        {},
        status.WARN,
        "motor is not enabled",
        False,
        id="disabled_drive",
    ),
    pytest.param(
        [(f"{MOTOR_PV}.CNEN", 0), (f"{MOTOR_PV}.DMOV", 1), (f"{MOTOR_PV}.MOVN", 0)],
        {"has_powerauto": False},
        status.WARN,
        "motor is not enabled",
        False,
        id="no_powerauto_and_disabled_drive",
    ),
    pytest.param(
        [(f"{MOTOR_PV}.DMOV", 1), (f"{MOTOR_PV}.MOVN", 0), (f"{MOTOR_PV}.MISS", 1)],
        {},
        status.NOTREACHED,
        "did not reach target",
        False,
        id="miss",
    ),
    pytest.param(
        [(f"{MOTOR_PV}.DMOV", 0), (f"{MOTOR_PV}.MOVN", 1), (f"{MOTOR_PV}.MISS", 1)],
        {},
        status.NOTREACHED,
        "did not reach target",
        False,
        id="miss_takes_precedence_over_busy",
    ),
    pytest.param(
        [(f"{MOTOR_PV}.DMOV", 1), (f"{MOTOR_PV}.MOVN", 0), (f"{MOTOR_PV}.LVIO", 1)],
        {},
        status.WARN,
        "soft limit violation",
        False,
        id="softlimit",
    ),
    pytest.param(
        [(f"{MOTOR_PV}.DMOV", 1), (f"{MOTOR_PV}.MOVN", 0), (f"{MOTOR_PV}.LLS", 1)],
        {},
        status.WARN,
        "low limit switch",
        False,
        id="low_limit_switch",
    ),
    pytest.param(
        [(f"{MOTOR_PV}.DMOV", 1), (f"{MOTOR_PV}.MOVN", 0), (f"{MOTOR_PV}.HLS", 1)],
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
        [(f"{MOTOR_PV}.LVIO", 1)],
        status.WARN,
        "soft limit violation",
        False,
        id="softlimit_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [(f"{MOTOR_PV}.LLS", 1)],
        status.WARN,
        "low limit switch",
        False,
        id="low_limit_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [(f"{MOTOR_PV}.HLS", 1)],
        status.WARN,
        "high limit switch",
        False,
        id="high_limit_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [(f"{MOTOR_PV}.MISS", 1)],
        status.NOTREACHED,
        "did not reach target",
        False,
        id="miss_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [(f"{MOTOR_PV}.DMOV", 0), (f"{MOTOR_PV}.MOVN", 1)],
        status.BUSY,
        "moving to",
        False,
        id="moving_message_overrides_ok_msgtxt_text",
    ),
    pytest.param(
        (status.OK, ""),
        0,
        "hello",
        [(f"{MOTOR_PV}-PwrAuto", 0), (f"{MOTOR_PV}.CNEN", 0)],
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
        (status.ERROR, "STATE"),
        1,
        "W: Axis not homed",
        [],
        status.ERROR,
        "W: Axis not homed, motor alarm: STATE",
        False,
        id="motor_alarm_and_msgtxt_both_shown_when_motor_more_severe",
    ),
    pytest.param(
        (status.WARN, "record alarm"),
        1,
        "minor issue",
        [],
        status.WARN,
        "minor issue, motor alarm: record alarm",
        False,
        id="motor_alarm_and_msgtxt_both_shown_when_same_severity",
    ),
    pytest.param(
        (status.WARN, "record alarm"),
        2,
        "major issue",
        [],
        status.ERROR,
        "major issue, motor alarm: record alarm",
        False,
        id="motor_alarm_and_msgtxt_both_shown_when_msgtxt_more_severe",
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
    pytest.param(
        (status.OK, ""),
        3,
        "invalid issue",
        [(f"{MOTOR_PV}.DMOV", 0), (f"{MOTOR_PV}.MOVN", 1), (f"{MOTOR_PV}.MISS", 1)],
        status.UNKNOWN,
        "invalid issue",
        False,
        id="unknown_takes_precedence_over_busy_and_notreached",
    ),
    pytest.param(
        (status.WARN, "record alarm"),
        0,
        "",
        [(f"{MOTOR_PV}.DMOV", 0), (f"{MOTOR_PV}.MOVN", 1)],
        status.BUSY,
        "record alarm",
        False,
        id="busy_takes_precedence_over_warn",
    ),
]


START_STATUS_TRANSITION_CASES = [
    pytest.param(
        # state before start
        [(f"{MOTOR_PV}.DMOV", 0), (f"{MOTOR_PV}.MOVN", 0), (f"{MOTOR_PV}.MISS", 0)],
        # alarm and message context
        (status.OK, ""),
        3,
        "invalid issue",
        # updates after start
        [],
        status.UNKNOWN,
        "invalid issue",
        False,
        status.UNKNOWN,
        "invalid issue",
        False,
        id="start_does_not_mask_unknown_with_busy",
    ),
    pytest.param(
        # state before start
        [(f"{MOTOR_PV}.DMOV", 1), (f"{MOTOR_PV}.MOVN", 0), (f"{MOTOR_PV}.MISS", 1)],
        # alarm and message context
        (status.OK, ""),
        0,
        "",
        # updates after start
        [
            (f"{MOTOR_PV}.MISS", 0),
            (f"{MOTOR_PV}.DMOV", 0),
            (f"{MOTOR_PV}.MOVN", 1),
        ],
        status.NOTREACHED,
        "did not reach target",
        False,
        status.BUSY,
        "moving to",
        False,
        id="status_switches_to_busy_when_miss_clears_during_move",
    ),
]


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
