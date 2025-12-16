import pytest

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
    }

    def doPreinit(self, mode):
        pass

    def doInit(self, mode):
        self._ps_bank = self.get_ps_bank()

    def _put_pv(self, pvparam, value, wait=False):
        self._record_fields[pvparam] = value

    def _get_pv(self, pvparam, as_string=False):
        return self._record_fields[pvparam]



class TestLokiDetectorCarriage:

    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.session.loadSetup("ess_power_supply", {})
        self.session.loadSetup("ess_loki_detector_carriage", {})
        self.ps_channel = self.session.getDevice("ps_channel_1")
        self.ps_bank = self.session.getDevice("ps_bank_hv")
        self.motor = self.session.getDevice("restricted_motor")
        yield
        self.session.unloadSetup()

    def test_move_ok_if_channel_off_and_voltage_zero(self):
        voltage = 0.0
        self.ps_bank.doEnable(False)
        self.ps_channel._record_fields["voltage_monitor"] = voltage
        self.motor.move(20)

    def test_move_ok_if_channel_off_and_voltage_below_threshold(self):
        voltage = 5.0
        self.ps_bank.doEnable(False)
        self.ps_channel._record_fields["voltage_monitor"] = voltage
        self.motor.move(20)

    def test_move_blocked_if_bank_on(self):
        self.ps_bank.doEnable(True)
        with pytest.raises(Exception):
            self.motor.move(20)

    def test_move_blocked_if_channel_on(self):
        self.ps_channel.doEnable(True)
        with pytest.raises(Exception):
            self.motor.move(20)

    def test_move_blocked_if_voltage_above_threshold(self):
        voltage = 5.1
        self.ps_bank.doEnable(False)
        self.ps_channel._record_fields["voltage_monitor"] = voltage
        with pytest.raises(Exception):
            self.motor.move(20)

