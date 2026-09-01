import pytest

from nicos.core import status
from nicos_ess.devices.epics.power_supply_group import PowerSupplyGroup

session_setup = None


class FakePowerSupplyGroup(PowerSupplyGroup):
    def doPreinit(self, mode):
        self._source_ids = tuple(self.sources)
        self.valuetype = float
        self._voltage = 0.0
        self._voltage_target = 800.0
        self._currents = 0.0
        self._current_limits = 10.0
        self._powered = False
        self._hardware_status = status.OK, ""
        self.parameters["currents"].unit = "uA"
        self.parameters["current_limits"].unit = "uA"

    @property
    def voltage(self):
        return self._voltage

    @voltage.setter
    def voltage(self, value):
        self._voltage = value
        self._cache.invalidate(self, "value")

    @property
    def powered(self):
        return self._powered

    @property
    def hardware_status(self):
        return self._hardware_status

    @hardware_status.setter
    def hardware_status(self, value):
        self._hardware_status = value

    def doInit(self, mode):
        pass

    def doRead(self, maxage=0):
        return self.voltage

    def doReadTarget(self):
        return self._voltage_target

    def doReadCurrents(self):
        return self._currents

    def doReadCurrent_Limits(self):
        return self._current_limits

    def doReadUnit(self):
        return "V"

    def doStart(self, target):
        self._voltage_target = target

    def doWriteCurrent_Limits(self, value):
        self._current_limits = value
        return value

    def doEnable(self, on):
        self._powered = on

    def doStatus(self, maxage=0):
        if self.hardware_status != (status.OK, ""):
            return self.hardware_status
        if not self.powered:
            if (
                self.voltage_off_threshold is not None
                and abs(self.voltage) > self.voltage_off_threshold
            ):
                return status.BUSY, "waiting for output voltage to decay"
            return status.DISABLED, "output disabled"
        return status.OK, "output enabled"


class TestPowerSupply:
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.session.loadSetup("ess_power_supply", {})
        self.power_supply = self.session.getDevice("ps_bank_hv")
        yield
        self.session.unloadSetup()

    def test_enable(self):
        self.power_supply.enable()
        assert self.power_supply.powered

    def test_disable(self):
        self.power_supply.enable()
        self.power_supply.disable()
        assert not self.power_supply.powered
