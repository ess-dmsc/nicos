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


def user_limits_from_dial_limits(direction, offset, dial_min, dial_max):
    if direction == "Pos":
        return dial_min + offset, dial_max + offset
    return -dial_max + offset, -dial_min + offset


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

    def test_motor_userlimits_can_be_written_when_direction_is_negative(
        self, device_harness, fake_backend
    ):
        fake_backend.values["SIM:M1.DLLM"] = -100.0
        fake_backend.values["SIM:M1.DHLM"] = 150.0
        fake_backend.values["SIM:M1.OFF"] = 10.0
        fake_backend.values["SIM:M1.DIR"] = "Neg"
        fake_backend.values["SIM:M1.LLM"] = -140.0
        fake_backend.values["SIM:M1.HLM"] = 110.0
        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMotor,
            name="motor",
            shared=default_motor_cfg(),
        )

        device_harness.run_daemon(daemon_device.doWriteUserlimits, (-130.0, 100.0))
        assert daemon_device.userlimits == (-130.0, 100.0)

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

    def test_motor_userlimits_does_not_change_abslimits(self, device_harness, fake_backend):
        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMotor,
            name="motor",
            shared=default_motor_cfg(),
        )
        assert daemon_device.abslimits == (-120.0, 120.0)
        assert daemon_device.userlimits == (-120.0, 120.0)

        device_harness.run_daemon(daemon_device.doWriteUserlimits, (-100.0, 100.0))

        assert daemon_device.abslimits == (-120.0, 120.0)
        assert daemon_device.userlimits == (-100.0, 100.0)
