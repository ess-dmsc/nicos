from unittest.mock import patch

import numpy as np
import pytest

pytest.importorskip("streaming_data_types")

from nicos.commands.measure import count
from nicos.commands.scan import scan

from nicos_ess.devices.epics.area_detector import AreaDetector

from test.nicos_ess.test_commands.conftest import _set_detectors, loaded_setup

session_setup = None


class CountingFakeAreaDetector(AreaDetector):
    """Area-detector test double with backend-driven completion."""

    _initial_fake_values = {
        "detector_state.STAT": 0,
        "detector_state.SEVR": 0,
        "max_size_x": 4,
        "max_size_y": 4,
        "readpv": 0,
        "detector_state": 0,
        "array_rate_rbv": "ArrayRate_RBV",
        "acquire": 0,
        "acquire_status": "Done",
    }

    def doPreinit(self, mode):
        self._fake_values = dict(self._initial_fake_values)
        self._fake_values["image_pv"] = np.arange(16, dtype=np.uint32)
        with patch("nicos_ess.devices.epics.area_detector.EpicsDevice"):
            super().doPreinit(mode)

    def _put_pv(self, pvparam, value, wait=False):
        self._fake_values[pvparam] = value
        if pvparam != "acquire":
            return
        if value:
            if self.iscontroller:
                self._fake_values["readpv"] = self.preselection
                self._fake_values["acquire_status"] = "Done"
            else:
                self._fake_values["acquire_status"] = "Acquiring"
        else:
            self._fake_values["acquire_status"] = "Done"

    def _get_pv(self, pvparam, as_string=False):
        return self._fake_values[pvparam]


def test_area_detector_count_with_timer_preset(session):
    with loaded_setup(session, "ess_area_detector_count_scan"):
        _set_detectors(session, "ad_collector")
        count(t=0.02)
        assert session.getDevice("ad_1")._fake_values["acquire_status"] == "Done"


def test_area_detector_count_with_explicit_channel_preset(session):
    with loaded_setup(session, "ess_area_detector_count_scan"):
        _set_detectors(session, "ad_collector")
        count(ad_1=1)
        assert session.getDevice("ad_1").read()[0] == 1


def test_area_detector_scan_across_two_points(session):
    with loaded_setup(session, "ess_area_detector_count_scan"):
        _set_detectors(session, "ad_collector")
        axis = session.getDevice("axis")
        scan(axis, 0, 1, 2, t=0.02)
        dataset = session.experiment.data.getLastScans()[-1]
        assert dataset.devvaluelists == [[0.0], [1.0]]
