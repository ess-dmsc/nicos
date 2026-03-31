"""
Tests for parameter override cleanup.

These tests verify that resolved parameter attributes are correct after
removing dead-code and redundant overrides from nicos_ess device classes.
"""

import pytest


class TestKnauerValveOverrides:
    """KnauerValve(EpicsDevice, CanReference, Moveable) — dead-code removal."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from nicos_ess.loki.devices.knauer_valve import KnauerValve
        self.cls = KnauerValve

    def test_readpv_not_in_parameters(self):
        assert "readpv" not in self.cls.parameters

    def test_writepv_not_in_parameters(self):
        assert "writepv" not in self.cls.parameters

    def test_mapping_not_in_parameters(self):
        assert "mapping" not in self.cls.parameters

    def test_unit_override(self):
        p = self.cls.parameters["unit"]
        assert p.mandatory is False
        assert p.settable is False
        assert p.default == ""

    def test_fmtstr_override(self):
        p = self.cls.parameters["fmtstr"]
        assert p.default == "%d"


class TestIDS3010ControlOverrides:
    """IDS3010Control(EpicsAnalogMoveable) — dead-code removal."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from nicos_ess.estia.devices.attocube import IDS3010Control
        self.cls = IDS3010Control

    def test_statuspv_not_in_parameters(self):
        assert "statuspv" not in self.cls.parameters

    def test_unit_override(self):
        p = self.cls.parameters["unit"]
        assert p.mandatory is False
        assert p.settable is False
        assert p.userparam is False
        assert p.default == ""

    def test_target_override(self):
        p = self.cls.parameters["target"]
        assert p.userparam is False


class TestRheometerControlOverrides:
    """RheometerControl(EpicsDevice, Moveable) — dead-code removal."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from nicos_ess.devices.epics.ap_rheometer import RheometerControl
        self.cls = RheometerControl

    def test_mapping_not_in_parameters(self):
        assert "mapping" not in self.cls.parameters

    def test_unit_override(self):
        p = self.cls.parameters["unit"]
        assert p.mandatory is False
        assert p.settable is False
        assert p.userparam is False


class TestChopperAlarmsOverrides:
    """ChopperAlarms(EpicsParameters, Readable) — redundant attribute removal."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from nicos_ess.devices.epics.chopper import ChopperAlarms
        self.cls = ChopperAlarms

    def test_unit_volatile_false(self):
        p = self.cls.parameters["unit"]
        assert p.volatile is False

    def test_unit_mandatory_false(self):
        p = self.cls.parameters["unit"]
        assert p.mandatory is False

    def test_unit_settable_false(self):
        p = self.cls.parameters["unit"]
        assert p.settable is False


class TestEssChopperControllerOverrides:
    """EssChopperController(MappedMoveable) — redundant attribute removal."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from nicos_ess.devices.epics.chopper import EssChopperController
        self.cls = EssChopperController

    def test_mapping_settable_false(self):
        p = self.cls.parameters["mapping"]
        assert p.settable is False

    def test_mapping_mandatory_false(self):
        p = self.cls.parameters["mapping"]
        assert p.mandatory is False

    def test_mapping_userparam_false(self):
        p = self.cls.parameters["mapping"]
        assert p.userparam is False

    def test_mapping_volatile_true(self):
        p = self.cls.parameters["mapping"]
        assert p.volatile is True


class TestHPLCPumpControllerOverrides:
    """HPLCPumpController(EpicsParameters, MappedMoveable) — redundant attribute removal."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from nicos_ess.devices.epics.hplc_pump import HPLCPumpController
        self.cls = HPLCPumpController

    def test_mapping_settable_false(self):
        p = self.cls.parameters["mapping"]
        assert p.settable is False

    def test_mapping_mandatory_false(self):
        p = self.cls.parameters["mapping"]
        assert p.mandatory is False

    def test_mapping_userparam_false(self):
        p = self.cls.parameters["mapping"]
        assert p.userparam is False

    def test_mapping_volatile_true(self):
        p = self.cls.parameters["mapping"]
        assert p.volatile is True


class TestSyringePumpControllerOverrides:
    """SyringePumpController(EpicsParameters, MappedMoveable) — redundant attribute removal."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from nicos_ess.devices.epics.syringe_pump import SyringePumpController
        self.cls = SyringePumpController

    def test_mapping_settable_false(self):
        p = self.cls.parameters["mapping"]
        assert p.settable is False

    def test_mapping_mandatory_false(self):
        p = self.cls.parameters["mapping"]
        assert p.mandatory is False

    def test_mapping_userparam_false(self):
        p = self.cls.parameters["mapping"]
        assert p.userparam is False

    def test_mapping_volatile_true(self):
        p = self.cls.parameters["mapping"]
        assert p.volatile is True
