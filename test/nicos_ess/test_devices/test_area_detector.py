#!/usr/bin/env python3
from unittest.mock import patch
import pytest
import numpy as np
from nicos.core.params import ArrayDesc
from nicos_ess.devices.epics.area_detector import AreaDetector

session_setup = None


class FakeAreaDetector(AreaDetector):
    """Area detector faking a connection."""

    fake_values = {
        "detector_state.STAT": 0,
        "detector_state.SEVR": 0,
        "max_size_x": 1024,
        "max_size_y": 2048,
        "data_type": np.uint32,
        "readpv": 0,
        "detector_state": 0,
        "array_rate_rbv": "ArrayRate_RBV",
        "acquire": "Acquire",
        "acquire_status": "AcquireBusy",
    }

    def doPreinit(self, mode):
        with patch("nicos_ess.devices.epics.area_detector.EpicsDevice"):
            super().doPreinit(mode)

    def _put_pv(self, pvparam, value, wait=False):
        self.fake_values[pvparam] = value

    def _get_pv(self, pvparam, as_string=False):
        return self.fake_values[pvparam]


class TestAreaDetector:
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.session.loadSetup("ess_area_detector", {})
        self.area_detector = self.session.getDevice("ad_1")
        yield
        self.session.unloadSetup()

    def test_array_info(self):
        """Test that arrayInfo() returns tuple of ArrayDesc."""
        ret = self.area_detector.arrayInfo()
        assert isinstance(ret, tuple)
        assert isinstance(ret[0], ArrayDesc)

    def test_completed(self):
        """Test that doIsCompleted() returns correct value."""
        self.area_detector.fake_values["acquire_status"] = "Done"
        ret = self.area_detector.isCompleted()
        assert ret == True
        self.area_detector.fake_values["acquire_status"] = "Busybusybusy"
        ret = self.area_detector.isCompleted()
        assert ret == False
