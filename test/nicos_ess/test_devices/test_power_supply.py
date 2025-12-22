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
        self._inverse_mapping = {}
        for k, v in self.mapping.items():
            self._inverse_mapping[v] = k

    def _put_pv(self, pvparam, value, wait=False):
        self._record_fields[pvparam] = value
        if pvparam == "power":
            self._simulate_power_on_or_off(value)

    def _get_pv(self, pvparam, as_string=False):
        return self._record_fields[pvparam]

    def _simulate_power_on_or_off(self, value):
        self._put_pv("power_rb", value)
        self._put_pv("status_on", bool(value))

    def doReadVoltage_Monitor(self):
        return self._get_pv("voltage_monitor")


class FakePowerSupplyBank(PowerSupplyBank):
    def doPreinit(self, mode):
        pass

    def doInit(self, mode):
        self._inverse_mapping = {}
        for k, v in self.mapping.items():
            self._inverse_mapping[v] = k


class TestPowerSupply:

    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.ps_channel = self.session.getDevice("ps_channel_1")
        self.ps_bank = self.session.getDevice("ps_bank_hv")

    def test_enable_ps_channel(self):
        self.ps_channel.enable()
        assert self.ps_channel._get_pv("power") == 1

    def test_disable_ps_channel(self):
        self.ps_channel.disable()
        assert self.ps_channel._get_pv("power") == 0

    def test_enable_ps_bank(self):
        self.ps_bank.enable()
        assert self.ps_channel._get_pv("power") == 1
        assert self.ps_bank.status_on() == (True, 1)

    def test_disable_ps_bank(self):
        self.ps_bank.disable()
        assert self.ps_channel._get_pv("power") == 0
        assert self.ps_bank.status_on() == (False, 0)
