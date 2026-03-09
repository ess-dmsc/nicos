import pytest
import threading

from nicos.core import LimitError, status
from nicos_ess.loki.devices.detector_motion import LOKIDetectorMotion

session_setup = None


class FakeLokiDetectorMotion(LOKIDetectorMotion):
    position = 10

    _record_fields = {
        "speed": 10,
        "position": position,
        "stop": 0,
        "lowlimit": -110,
        "highlimit": 110,
        "readpv": position,
        "writepv": position,
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
        self._ps_bank = self._get_ps_bank()

    def doInit(self, mode):
        pass

    def _put_pv(self, pvparam, value, wait=False):
        self._record_fields[pvparam] = value

    def _get_pv(self, pvparam, as_string=False):
        return self._record_fields[pvparam]

    def _get_cached_pv_or_ask(self, param, as_string=False):
        return self._get_pv(param, as_string)


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
            self.motor, "_get_alarm_status_and_msg", lambda: (status.OK, "")
        )
        yield
        self.ps_channel._record_fields = {
            "voltage_monitor": 0.0,
            "current_monitor": 0.0,
            "power_rb": 0,
            "power": 0,
            "status_on": False,
        }
        self.session.unloadSetup()

    def test_movement_allowed_if_channel_off_and_voltage_zero(self):
        voltage = 0.0
        self.ps_bank.enable()
        self.ps_bank.disable()
        self.ps_channel._put_pv("voltage_monitor", voltage)
        self.motor.move(20)

    def test_movement_allowed_if_channel_off_and_voltage_below_threshold(self):
        voltage = self.motor.voltage_off_threshold - 0.1
        self.ps_bank.enable()
        self.ps_bank.disable()
        self.ps_channel._put_pv("voltage_monitor", voltage)
        self.motor.move(20)

    def test_movement_blocked_if_bank_is_on(self):
        self.ps_bank.disable()
        self.ps_bank.enable()
        with pytest.raises(LimitError):
            self.motor.move(20)

    def test_movement_blocked_if_channel_is_on(self):
        self.ps_channel.disable()
        self.ps_channel.enable()
        with pytest.raises(LimitError):
            self.motor.move(20)

    def test_movement_blocked_if_voltage_above_threshold(self):
        voltage = self.motor.voltage_off_threshold + 0.1
        self.ps_bank.enable()
        self.ps_bank.disable()
        self.ps_channel._put_pv("voltage_monitor", voltage)
        with pytest.raises(LimitError):
            self.motor.move(20)

    def test_movement_blocked_if_status_not_ok(self, monkeypatch):
        voltage = self.motor.voltage_off_threshold - 0.1
        error_status = (status.ERROR, "some error message")
        monkeypatch.setattr(type(self.ps_bank), "doStatus", lambda: error_status)
        self.ps_bank.enable()
        self.ps_bank.disable()
        self.ps_channel._put_pv("voltage_monitor", voltage)
        with pytest.raises(LimitError):
            self.motor.move(20)
