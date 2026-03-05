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



"""
LIMITS examples from an actual EPICS motor record with offset and direction set:

Positive direction:
IOC:m1.DIR 2026-03-05 09:20:07.116  (0) Pos
IOC:m1.OFF 2026-03-05 09:20:07.116  10 
IOC:m1.DLLM 2026-03-05 09:20:07.116  -100 
IOC:m1.DHLM 2026-03-05 09:20:07.116  150 
IOC:m1.LLM 2026-03-05 09:20:07.116  -90 
IOC:m1.HLM 2026-03-05 09:20:07.116  160 


Negative direction:
IOC:m1.DIR 2026-03-05 09:22:11.352  (1) Neg
IOC:m1.OFF 2026-03-05 09:22:11.352  10 
IOC:m1.DLLM 2026-03-05 09:22:11.352  -100 
IOC:m1.DHLM 2026-03-05 09:22:11.352  150 
IOC:m1.LLM 2026-03-05 09:22:11.352  -140 
IOC:m1.HLM 2026-03-05 09:22:11.352  110 

"""

DIR_CONFIGS = {
    "Pos": {
        "DIR": "Pos",
        "OFF": 10.0,
        "DLLM": -100.0,
        "DHLM": 150.0,
        "LLM": -90.0,
        "HLM": 160.0,
    },
    "Neg": {
        "DIR": "Neg",
        "OFF": 10.0,
        "DLLM": -100.0,
        "DHLM": 150.0,
        "LLM": -140.0,
        "HLM": 110.0,
    },
}


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

    def test_motor_limits_are_read_when_motorrecord_offset_is_nonzero(self, device_harness, fake_backend):
        fake_backend.values["SIM:M1.OFF"] = 10.0
        fake_backend.values["SIM:M1.LLM"] = -110.0
        fake_backend.values["SIM:M1.HLM"] = 130.0
        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMotor,
            name="motor",
            shared=default_motor_cfg(),
        )
        assert daemon_device.abslimits == (-120.0, 120.0)
        assert daemon_device.userlimits == (-110.0, 130.0)

    def test_motor_limits_are_read_when_motorrecord_offset_is_larger_than_limits(self, device_harness, fake_backend):
        fake_backend.values["SIM:M1.OFF"] = 150.0
        fake_backend.values["SIM:M1.LLM"] = 30.0
        fake_backend.values["SIM:M1.HLM"] = 270.0
        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMotor,
            name="motor",
            shared=default_motor_cfg(),
        )
        assert daemon_device.abslimits == (-120.0, 120.0)
        assert daemon_device.userlimits == (30.0, 270.0)

    def test_motor_limits_are_read_when_direction_is_negative(self, device_harness, fake_backend):
        fake_backend.values["SIM:M1.OFF"] = 10.0
        fake_backend.values["SIM:M1.DIR"] = "Neg"
        fake_backend.values["SIM:M1.LLM"] = -110.0
        fake_backend.values["SIM:M1.HLM"] = 130.0
        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMotor,
            name="motor",
            shared=default_motor_cfg(),
        )
        assert daemon_device.abslimits == (-120.0, 120.0)
        assert daemon_device.userlimits == (-110.0, 130.0)

    def test_motor_limits_are_read_when_direction_is_negative_and_dial_limits_are_asymmetric(
        self, device_harness, fake_backend
    ):
        fake_backend.values["SIM:M1.DLLM"] = -100.0
        fake_backend.values["SIM:M1.DHLM"] = 150.0
        fake_backend.values["SIM:M1.OFF"] = 10.0
        fake_backend.values["SIM:M1.DIR"] = "Neg"
        fake_backend.values["SIM:M1.LLM"] = -140.0 # 150 -> -140 because direction is negative (swap limits) and offset is 10
        fake_backend.values["SIM:M1.HLM"] = 110.0
        daemon_device, _poller_device = device_harness.create_pair(
            EpicsMotor,
            name="motor",
            shared=default_motor_cfg(),
        )
        assert daemon_device.abslimits == (-100.0, 150.0)
        assert daemon_device.hwuserlimits == (-140.0, 110.0)
        assert daemon_device.userlimits == (-140.0, 110.0)

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
