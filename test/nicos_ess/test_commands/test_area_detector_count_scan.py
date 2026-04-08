import pytest

from nicos.commands.measure import count
from nicos.commands.scan import scan
from nicos.devices.epics.pva import caproto, p4p

from test.nicos_ess.command_helpers import (
    loaded_setup,
    scan_positions,
    set_detectors,
)
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend

session_setup = None

PV_ROOT = "SIM:AD:"
IMAGE_PV = f"{PV_ROOT}IMAGE"


def _pv(suffix):
    return f"{PV_ROOT}{suffix}"


def _seed_backend(backend):
    backend.values.update(
        {
            _pv("MaxSizeX_RBV"): 4,
            _pv("MaxSizeY_RBV"): 4,
            _pv("DataType_RBV"): "UInt32",
            _pv("NumImagesCounter_RBV"): 0,
            _pv("DetectorState_RBV"): 0,
            _pv("DetectorState_RBV.STAT"): 0,
            _pv("DetectorState_RBV.SEVR"): 0,
            _pv("ArrayRate_RBV"): 1.0,
            _pv("Acquire"): 0,
            _pv("AcquireBusy"): "Done",
            IMAGE_PV: list(range(16)),
        }
    )


@pytest.fixture
def area_detector_backend(monkeypatch):
    backend = FakeEpicsBackend()
    backend.close_subscription = lambda token: None
    monkeypatch.setattr(p4p, "P4pWrapper", lambda timeout: backend)
    monkeypatch.setattr(caproto, "CaprotoWrapper", lambda timeout: backend)
    _seed_backend(backend)

    original_put = backend.put_pv_value

    def put_pv_value(pvname, value, wait=False):
        original_put(pvname, value, wait=wait)
        if pvname != _pv("Acquire"):
            return
        if value:
            backend.values[_pv("NumImagesCounter_RBV")] = 1
        backend.values[_pv("AcquireBusy")] = "Done"

    backend.put_pv_value = put_pv_value
    return backend


def test_area_detector_count_with_timer_preset(session, area_detector_backend):
    with loaded_setup(session, "ess_area_detector_count_scan"):
        set_detectors(session, "ad_collector")
        count(t=0.02)
        acquire_values = [
            value
            for pvname, value, _wait in area_detector_backend.put_calls
            if pvname == _pv("Acquire")
        ]
        assert acquire_values == [1, 0]


def test_area_detector_count_with_explicit_channel_preset(
    session, area_detector_backend
):
    del area_detector_backend
    with loaded_setup(session, "ess_area_detector_count_scan"):
        set_detectors(session, "ad_collector")
        count(ad_1=1)
        assert session.getDevice("ad_1").read()[0] == 1


def test_area_detector_scan_across_two_points(session, area_detector_backend):
    del area_detector_backend
    with loaded_setup(session, "ess_area_detector_count_scan"):
        set_detectors(session, "ad_collector")
        axis = session.getDevice("axis")
        scan(axis, 0, 1, 2, t=0.02)
        dataset = session.experiment.data.getLastScans()[-1]
        assert scan_positions(dataset) == [0.0, 1.0]
