import pytest

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
    fake_backend.values[f"{motorpv}.DIR"] = "Pos" # enum string value
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


    def test_motor_limits_are_read_when_starting(self, device_harness, fake_backend):
        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMotor,
            name="motor",
            shared=default_motor_cfg(),
        )
        assert daemon_device.abslimits == (-120.0, 120.0)
        assert daemon_device.userlimits == (-120.0, 120.0)

    def test_motor_limits_are_read_when_motorrecord_offset_is_larger_than_limits(self, device_harness, fake_backend):
        fake_backend.values["SIM:M1.OFF"] = 150.0
        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMotor,
            name="motor",
            shared={**default_motor_cfg(), "motorpv": "SIM:M1", "has_foff": True},
        )
        assert daemon_device.abslimits == (-120.0, 120.0)
        assert daemon_device.userlimits == (30.0, 270.0)

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

