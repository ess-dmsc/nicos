import pytest

from nicos_ess.devices.epics.power_supply_channel import (
    PowerSupplyBank,
    PowerSupplyChannel,
)
from test.nicos_ess.test_devices.doubles.epics_pva_backend import FakeEpicsComponent

session_setup = None


class FakePowerSupplyComponent(FakeEpicsComponent):
    def put_channel_value(self, channel, value):
        self.values[channel] = value
        if channel == "power":
            self.values["power_rb"] = value
            self.values["status_on"] = bool(value)


def initial_channel_values():
    return {
        "voltage_monitor": 0.0,
        "current_monitor": 0.0,
        "power_rb": 0,
        "power": 0,
        "status_on": False,
    }


class FakePowerSupplyChannel(PowerSupplyChannel):
    def doPreinit(self, mode):
        self._epics = FakePowerSupplyComponent(initial_channel_values())

    def doInit(self, mode):
        self._inverse_mapping = {}
        for k, v in self.mapping.items():
            self._inverse_mapping[v] = k

    def _read_channel_cached(self, channel, as_string=None, maxage=None):
        return self._epics.values[channel]


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
        self.session.loadSetup("ess_power_supply", {})
        self.ps_channel = self.session.getDevice("ps_channel_1")
        self.ps_bank = self.session.getDevice("ps_bank_hv")
        yield
        self.session.unloadSetup()

    def test_enable_ps_channel(self):
        self.ps_channel.enable()
        assert self.ps_channel._epics.values["power"] == 1

    def test_disable_ps_channel(self):
        self.ps_channel.disable()
        assert self.ps_channel._epics.values["power"] == 0

    def test_enable_ps_bank(self):
        self.ps_bank.enable()
        assert self.ps_channel._epics.values["power"] == 1
        assert self.ps_bank.status_on() == (True, 1)

    def test_disable_ps_bank(self):
        self.ps_bank.disable()
        assert self.ps_channel._epics.values["power"] == 0
        assert self.ps_bank.status_on() == (False, 0)
