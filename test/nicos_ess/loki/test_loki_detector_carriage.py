import threading

import pytest

from nicos.core import LimitError, status
from nicos_ess.loki.devices.detector_motion import LOKIDetectorMotion
from test.nicos_ess.test_devices.doubles.epics_pva_backend import FakeEpicsComponent
from test.nicos_ess.test_devices.test_power_supply import initial_channel_values

session_setup = None


class FakeLokiDetectorMotion(LOKIDetectorMotion):
    position = 10

    @classmethod
    def _initial_record_fields(cls):
        return {
            "speed": 10,
            "position": cls.position,
            "stop": 0,
            "lowlimit": -110,
            "highlimit": 110,
            "readpv": cls.position,
            "writepv": cls.position,
            "offset": 0,
            "enable": 1,
            "direction": 0,
            "unit": "mm",
            "target": 45,
            "position_deadband": 0.1,
            "diallowlimit": -120,
            "dialhighlimit": 120,
            "dir": "Pos",
            "description": "motor1 test device",
            "monitor_deadband": 0.2,
            "moving": False,
            "donemoving": True,
            "value": 0,
            "dialvalue": 0,
            "miss": 0,
            "lowlimitswitch": 0,
            "highlimitswitch": 100,
        }

    def doPreinit(self, mode):
        self._lock = threading.Lock()
        self._motor_status = (status.OK, "")
        self._epics_channels = self._initial_record_fields()
        self._epics = FakeEpicsComponent(self._epics_channels)

    def doInit(self, mode):
        pass

    def _read_channel_cached(self, field, as_string=None, maxage=None):
        return self._epics_channels[field]

    def doReadUnit(self, maxage=None):
        return self._epics_channels["unit"]


class TestLokiDetectorCarriage:
    @pytest.fixture(autouse=True)
    def prepare(self, session, monkeypatch):
        self.session = session
        self.session.loadSetup("ess_power_supply", {})
        self.session.loadSetup("ess_loki_detector_carriage", {})
        self.ps_channel = self.session.getDevice("ps_channel_1")
        self.ps_bank = self.session.getDevice("ps_bank_hv")
        self.motor = self.session.getDevice("restricted_motor")
        monkeypatch.setattr(
            self.motor, "_get_alarm_status_and_msg", lambda maxage=0: (status.OK, "")
        )
        yield
        self.ps_channel._epics.values.update(initial_channel_values())
        self.session.unloadSetup()

    def test_movement_allowed_if_channel_off_and_voltage_zero(self):
        voltage = 0.0
        self.ps_bank.disable()
        self.ps_channel._epics.put_channel_value("voltage_monitor", voltage)
        self.motor.move(20)

    def test_movement_allowed_if_channel_off_and_voltage_below_threshold(self):
        voltage = self.motor.voltage_off_threshold - 0.1
        self.ps_bank.disable()
        self.ps_channel._epics.put_channel_value("voltage_monitor", voltage)
        self.motor.move(20)

    def test_movement_blocked_if_bank_is_on(self):
        self.ps_bank.enable()
        with pytest.raises(LimitError):
            self.motor.move(20)

    def test_movement_blocked_if_channel_is_on(self):
        self.ps_channel.enable()
        with pytest.raises(LimitError):
            self.motor.move(20)

    def test_movement_blocked_if_voltage_above_threshold(self):
        voltage = self.motor.voltage_off_threshold + 0.1
        self.ps_bank.disable()
        self.ps_channel._epics.put_channel_value("voltage_monitor", voltage)
        with pytest.raises(LimitError):
            self.motor.move(20)

    def test_movement_blocked_if_status_not_ok(self, monkeypatch):
        voltage = self.motor.voltage_off_threshold - 0.1
        error_status = (status.ERROR, "some error message")
        monkeypatch.setattr(
            type(self.ps_bank), "doStatus", lambda self, maxage=0: error_status
        )
        self.ps_bank.disable()
        self.ps_channel._epics.put_channel_value("voltage_monitor", voltage)
        with pytest.raises(LimitError):
            self.motor.move(20)

    def test_movement_blocked_if_pos_outside_limits(self):
        voltage = 0.0
        self.ps_bank.disable()
        self.ps_channel._epics.put_channel_value("voltage_monitor", voltage)
        with pytest.raises(LimitError):
            self.motor.move(200)
