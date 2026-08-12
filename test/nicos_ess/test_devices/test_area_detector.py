import pytest
import numpy as np

from nicos.core.params import ArrayDesc
from nicos_ess.devices.epics.area_detector import AreaDetector

from test.nicos_ess.test_devices.doubles.epics_pva_backend import FakeEpicsComponent

session_setup = None

class FakeAreaDetector(AreaDetector):
    """Area detector faking a connection."""
    @classmethod
    def _initial_channel_values(cls):
        return {
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
        self._epics = FakeEpicsComponent(self._initial_channel_values())

    def doInit(self, mode):
        pass

    def _read_channel_cached(self, channel, as_string=None, maxage=None):
        return self._epics.values[channel]


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
        self.area_detector._epics.values["acquire_status"] = "Done"
        ret = self.area_detector.isCompleted()
        assert ret
        self.area_detector._epics.values["acquire_status"] = "Busybusybusy"
        ret = self.area_detector.isCompleted()
        assert not ret
