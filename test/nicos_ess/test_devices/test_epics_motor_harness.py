import pytest

from nicos.core.errors import ConfigurationError
from nicos_ess.devices.epics.pva.motor import EpicsMotor
from nicos_ess.devices.epics.pva import motor
from test.nicos_ess.test_devices.doubles import patch_create_wrapper


@pytest.fixture
def fake_backend(monkeypatch):
    """Install a reusable fake EPICS backend for each test."""
    return patch_create_wrapper(monkeypatch, motor)


def default_motor_cfg():
    return {
        "motorpv": "SIM:M1",
        "has_powerauto": True,
        "has_msgtxt": True,
        "has_errorbit": True,
        "has_reseterror": True,
        "monitor_deadband": 0.1,
        "monitor": False,
    }


@pytest.fixture(autouse=True)
def default_motor_pvs(fake_backend):
    """Set up default PV values for a motor."""
    motorpv = "SIM:M1"
    fake_backend.values[f"{motorpv}.RBV"] = 2.5
    fake_backend.values[f"{motorpv}.DRBV"] = 2.5
    fake_backend.values[f"{motorpv}.VAL"] = 2.5
    fake_backend.values[f"{motorpv}.STOP"] = 0
    fake_backend.values[f"{motorpv}.VELO"] = 1.0
    fake_backend.values[f"{motorpv}.OFF"] = 0.0
    fake_backend.values[f"{motorpv}.HLM"] = 120.0
    fake_backend.values[f"{motorpv}.LLM"] = -120.0
    fake_backend.values[f"{motorpv}.DHLM"] = 120.0
    fake_backend.values[f"{motorpv}.DLLM"] = -120.0
    fake_backend.values[f"{motorpv}.CNEN"] = 1
    fake_backend.values[f"{motorpv}.SET"] = 0
    fake_backend.values[f"{motorpv}.FOFF"] = 0
    fake_backend.values[f"{motorpv}.DIR"] = "Pos"  # enum string value
    fake_backend.values[f"{motorpv}.EGU"] = "mm"
    fake_backend.values[f"{motorpv}.HOMF"] = 0
    fake_backend.values[f"{motorpv}.HOMR"] = 0
    fake_backend.values[f"{motorpv}.RDBD"] = 0.1
    fake_backend.values[f"{motorpv}.DESC"] = "Test Motor"
    fake_backend.values[f"{motorpv}.MDEL"] = 0.1
    fake_backend.values[f"{motorpv}.VMAX"] = 10.0
    fake_backend.values[f"{motorpv}.VBAS"] = 0.1
    fake_backend.values[f"{motorpv}.DMOV"] = 1
    fake_backend.values[f"{motorpv}.MOVN"] = 0
    fake_backend.values[f"{motorpv}.MISS"] = 0
    fake_backend.values[f"{motorpv}.STAT"] = 0
    fake_backend.values[f"{motorpv}.SEVR"] = 0
    fake_backend.values[f"{motorpv}.LVIO"] = 0
    fake_backend.values[f"{motorpv}.LLS"] = 0
    fake_backend.values[f"{motorpv}.HLS"] = 0
    fake_backend.values[f"{motorpv}-Err"] = 0
    fake_backend.values[f"{motorpv}-ErrRst"] = 0
    fake_backend.values[f"{motorpv}-PwrAuto"] = 1
    fake_backend.values[f"{motorpv}-MsgTxt"] = ""
    fake_backend.values[f"{motorpv}-MsgTxt.SEVR"] = 0


ASYMM_DIAL_LIMITS = (-100.0, 150.0)
OFFSET_CASES = [
    pytest.param(-200.0, id="large_negative_offset"),
    pytest.param(-10.0, id="small_negative_offset"),
    pytest.param(0.0, id="zero_offset"),
    pytest.param(10.0, id="small_positive_offset"),
    pytest.param(200.0, id="large_positive_offset"),
]
TARGET_DIAL_USERLIMITS = (-80.0, 120.0)
INITIAL_DYNAMIC_HW_DIAL_LIMITS = (-60.0, 120.0)
WRITTEN_DYNAMIC_USER_DIAL_LIMITS = (-40.0, 110.0)
DYNAMIC_HW_DIAL_LIMIT_CASES = [
    pytest.param((-30.0, 70.0), "smaller", id="hardware_tightens"),
    pytest.param((-85.0, 140.0), "larger", id="hardware_widens"),
    pytest.param((10.0, 30.0), "fallback", id="hardware_becomes_very_tight"),
]


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


class TestEpicsMotor:
    def test_motor_can_move_when_miss_is_set(self, device_harness, fake_backend):
        # Setup
        dev = device_harness.create(
            "daemon",
            EpicsMotor,
            name="motor",
            **default_motor_cfg(),
        )
        fake_backend.emit_update("SIM:M1.MISS", value=1)

        dev.move(5.0)
        assert fake_backend.values["SIM:M1.VAL"] == 5.0

    @pytest.mark.parametrize("offset", OFFSET_CASES)
    @pytest.mark.parametrize("direction", ["Pos", "Neg"], ids=["dir_pos", "dir_neg"])
    def test_motor_limits_are_read_for_all_direction_and_offset_cases_with_asymmetric_dial_limits(
        self, device_harness, fake_backend, direction, offset
    ):
        dial_min, dial_max = ASYMM_DIAL_LIMITS
        umin, umax = user_limits_from_dial_limits(direction, offset, dial_min, dial_max)
        fake_backend.values["SIM:M1.DLLM"] = dial_min
        fake_backend.values["SIM:M1.DHLM"] = dial_max
        fake_backend.values["SIM:M1.OFF"] = offset
        fake_backend.values["SIM:M1.DIR"] = direction
        fake_backend.values["SIM:M1.LLM"] = umin
        fake_backend.values["SIM:M1.HLM"] = umax
        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMotor,
            name="motor",
            shared=default_motor_cfg(),
        )
        assert daemon_device.abslimits == (dial_min, dial_max)
        assert daemon_device.hwuserlimits == (umin, umax)
        assert daemon_device.userlimits == (umin, umax)

    @pytest.mark.parametrize("offset", OFFSET_CASES)
    @pytest.mark.parametrize("direction", ["Pos", "Neg"], ids=["dir_pos", "dir_neg"])
    def test_motor_userlimits_are_written_for_all_direction_and_offset_cases_with_asymmetric_dial_limits(
        self, device_harness, fake_backend, direction, offset
    ):
        dial_min, dial_max = ASYMM_DIAL_LIMITS
        hw_umin, hw_umax = user_limits_from_dial_limits(
            direction, offset, dial_min, dial_max
        )
        fake_backend.values["SIM:M1.DLLM"] = dial_min
        fake_backend.values["SIM:M1.DHLM"] = dial_max
        fake_backend.values["SIM:M1.OFF"] = offset
        fake_backend.values["SIM:M1.DIR"] = direction
        fake_backend.values["SIM:M1.LLM"] = hw_umin
        fake_backend.values["SIM:M1.HLM"] = hw_umax
        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMotor,
            name="motor",
            shared=default_motor_cfg(),
        )

        target_dial_min, target_dial_max = TARGET_DIAL_USERLIMITS
        target_umin, target_umax = user_limits_from_dial_limits(
            direction, offset, target_dial_min, target_dial_max
        )
        device_harness.run_daemon(
            daemon_device.doWriteUserlimits, (target_umin, target_umax)
        )

        expected_omin = target_umin - hw_umin
        expected_omax = target_umax - hw_umax
        assert daemon_device.abslimits == (dial_min, dial_max)
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
        abs_dial_min, abs_dial_max = ASYMM_DIAL_LIMITS
        hw_dial_min, hw_dial_max = INITIAL_DYNAMIC_HW_DIAL_LIMITS
        hw_umin, hw_umax = user_limits_from_dial_limits(
            direction, offset, hw_dial_min, hw_dial_max
        )
        fake_backend.values["SIM:M1.DLLM"] = abs_dial_min
        fake_backend.values["SIM:M1.DHLM"] = abs_dial_max
        fake_backend.values["SIM:M1.OFF"] = offset
        fake_backend.values["SIM:M1.DIR"] = direction
        fake_backend.values["SIM:M1.LLM"] = hw_umin
        fake_backend.values["SIM:M1.HLM"] = hw_umax
        cfg = default_motor_cfg()
        cfg["monitor"] = True
        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMotor,
            name="motor",
            shared=cfg,
        )

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
        fake_backend.emit_update("SIM:M1.LLM", value=new_hw_umin)
        fake_backend.emit_update("SIM:M1.HLM", value=new_hw_umax)
        # Ensure daemon reads the monitor cache updates rather than backend values.
        fake_backend.values["SIM:M1.LLM"] = 999.0
        fake_backend.values["SIM:M1.HLM"] = -999.0

        expected_userlimits_after_update, expected_limitoffsets_after_update = (
            userlimits_from_hw_window_and_limitoffsets(
                new_hw_umin, new_hw_umax, expected_limitoffsets_before_update
            )
        )
        after_userlimits = device_harness.run_daemon(daemon_device.doReadUserlimits)
        assert daemon_device.abslimits == (abs_dial_min, abs_dial_max)
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

    def test_motor_limits_read_fails_when_record_limits_are_inconsistent(
        self, device_harness, fake_backend
    ):
        fake_backend.values["SIM:M1.OFF"] = 10.0
        # Keep default HLM/LLM from fixture (-120, 120), which is inconsistent
        # with OFF=10 and the dial limits.
        with pytest.raises(ConfigurationError):
            device_harness.create_pair(
                EpicsMotor,
                name="motor",
                shared=default_motor_cfg(),
            )
