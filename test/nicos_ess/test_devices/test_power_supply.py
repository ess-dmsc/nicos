import pytest


from nicos_ess.devices.epics.power_supply_channel import PowerSupplyChannel, PowerSupplyBank

session_setup = "ess_power_supply"

class FakePowerSupplyChannel(PowerSupplyChannel):

    _record_fields = {
        "voltage_monitor": 0.0,
        "current_monitor": 0.0,
        "power_rb": 0,
        "power": 0,
        "status_on": False,
    }

    def doPreinit(self, mode):
        pass

    def doInit(self, mode):
        pass

    def _put_pv(self, pvparam, value, wait=False):
        self._record_fields[pvparam] = value
        if pvparam == "power":
            self._simulate_power_on_or_off(value)

    def _get_pv(self, pvparam, as_string=False):
        return self._record_fields[pvparam]

    def _simulate_power_on_or_off(self, value):
        self._record_fields["power_rb"] = value
        self._record_fields["status_on"] = bool(value)

    def doReadVoltage_Monitor(self, as_string=False):
        return self._get_pv("voltage_monitor")

    def doReadCurrent_Monitor(self, as_string=False):
        return self._get_pv("current_monitor")


class FakePowerSupplyBank(PowerSupplyBank):
    def doPreinit(self, mode):
        pass

    def doInit(self, mode):
        pass


class TestPowerSupply:

    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.ps_channel = self.session.getDevice("ps_channel_1")
        self.ps_bank = self.session.getDevice("ps_bank_hv")

    def test_enable_ps_channel(self):
        self.ps_channel.doEnable(True)
        assert self.ps_channel._record_fields["power"] == 1

    def test_disable_ps_channel(self):
        self.ps_channel.doEnable(False)
        assert self.ps_channel._record_fields["power"] == 0

    def test_enable_ps_bank(self):
        self.ps_bank.doEnable(True)
        assert self.ps_channel._record_fields["power"] == 1
        assert self.ps_bank.status_on() == (True, 1)

    def test_disable_ps_bank(self):
        self.ps_bank.doEnable(False)
        assert self.ps_channel._record_fields["power"] == 0
        assert self.ps_bank.status_on() == (False, 0)
