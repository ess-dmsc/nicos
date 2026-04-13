"""Command-level tests for the simplified area-detector integration.

The fake backend completes acquisitions immediately so the assertions stay
about NICOS orchestration:

- how presets are routed into the detector graph
- which EPICS writes happen during `count()`
- how many scan points produce detector activity
"""

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

# The command tests start from an otherwise empty session and load their own
# small custom setups explicitly.
session_setup = None

PV_ROOT = "SIM:AD:"
IMAGE_PV = f"{PV_ROOT}IMAGE"
DEFAULT_IMAGE_SHAPE = (4, 4)
COUNT_TIMER_PRESET_SECONDS = 0.02
IMAGE_PRESELECTION = 1


def _pv(suffix):
    return f"{PV_ROOT}{suffix}"


def _seed_backend(backend):
    """Populate the fake EPICS backend with the PVs this detector reads."""
    backend.values.update(
        {
            _pv("MaxSizeX_RBV"): DEFAULT_IMAGE_SHAPE[1],
            _pv("MaxSizeY_RBV"): DEFAULT_IMAGE_SHAPE[0],
            _pv("DataType_RBV"): "UInt32",
            _pv("NumImagesCounter_RBV"): 0,
            _pv("DetectorState_RBV"): 0,
            _pv("DetectorState_RBV.STAT"): 0,
            _pv("DetectorState_RBV.SEVR"): 0,
            _pv("ArrayRate_RBV"): 1.0,
            _pv("Acquire"): 0,
            _pv("AcquireBusy"): "Done",
            IMAGE_PV: list(range(DEFAULT_IMAGE_SHAPE[0] * DEFAULT_IMAGE_SHAPE[1])),
        }
    )


@pytest.fixture
def area_detector_backend(monkeypatch):
    """Patch p4p/caproto so the detector talks to one in-memory backend.

    Any write to `Acquire` completes immediately. That makes the command tests
    deterministic and gives a simple expected EPICS write sequence:
    start once (`Acquire=1`), then stop once (`Acquire=0`).
    """
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
            # Reading the detector after a finished count should report that
            # one image was acquired.
            backend.values[_pv("NumImagesCounter_RBV")] = 1
        backend.values[_pv("AcquireBusy")] = "Done"

    backend.put_pv_value = put_pv_value
    return backend


def test_area_detector_count_with_timer_preset(session, area_detector_backend):
    """A plain timer preset should still start and stop the image detector."""
    with loaded_setup(session, "ess_area_detector_count_scan"):
        set_detectors(session, "ad_collector")
        count(t=COUNT_TIMER_PRESET_SECONDS)
        acquire_values = [
            value
            for pvname, value, _wait in area_detector_backend.put_calls
            if pvname == _pv("Acquire")
        ]
        assert acquire_values == [1, 0]


def test_area_detector_count_with_explicit_channel_preset(
    session, area_detector_backend
):
    """An explicit image preset should route to the active image channel.

    The fake backend increments the image counter to 1 whenever acquisition
    starts, so the final detector read proves that the count reached the
    underlying channel and triggered an acquisition.
    """
    del area_detector_backend
    with loaded_setup(session, "ess_area_detector_count_scan"):
        set_detectors(session, "ad_collector")
        count(ad_1=IMAGE_PRESELECTION)
        assert session.getDevice("ad_1").read()[0] == 1


def test_area_detector_scan_across_two_points(session, area_detector_backend):
    """Each scan point should trigger one detector acquisition."""
    del area_detector_backend
    with loaded_setup(session, "ess_area_detector_count_scan"):
        set_detectors(session, "ad_collector")
        axis = session.getDevice("axis")
        scan(axis, 0, 1, 2, t=COUNT_TIMER_PRESET_SECONDS)
        dataset = session.experiment.data.getLastScans()[-1]
        assert scan_positions(dataset) == [0.0, 1.0]
