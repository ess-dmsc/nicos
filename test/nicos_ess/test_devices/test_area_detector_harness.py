"""Harness tests for the simplified area-detector implementation.

These tests stay below the command layer and check the device graph directly:

- active-channel preset handling
- which object owns array metadata after the branch changes
"""

import numpy as np
import pytest

from nicos.core import FINAL
from nicos.devices.epics.pva import caproto, p4p
from nicos.devices.generic import ActiveChannel

from nicos_ess.devices.epics.area_detector import AreaDetector, \
    AreaDetectorCollector

from test.nicos_ess.test_devices.doubles import FakeEpicsBackend

PV_ROOT = "SIM:AD:"
IMAGE_PV = f"{PV_ROOT}IMAGE"
DEFAULT_IMAGE_SHAPE = (3, 4)
RESIZED_IMAGE_SHAPE = (2, 6)
IMAGE_PRESELECTION = 5


def _pv(suffix):
    return f"{PV_ROOT}{suffix}"


def _seed_backend(backend, *, shape=(3, 4), image=None):
    """Populate the fake EPICS backend with one consistent detector state."""
    if image is None:
        image = np.arange(np.prod(shape), dtype=np.uint32)
    backend.values.update(
        {
            _pv("MaxSizeX_RBV"): shape[1],
            _pv("MaxSizeY_RBV"): shape[0],
            _pv("DataType_RBV"): "UInt32",
            _pv("NumImagesCounter_RBV"): 0,
            _pv("DetectorState_RBV"): 0,
            _pv("DetectorState_RBV.STAT"): 0,
            _pv("DetectorState_RBV.SEVR"): 0,
            _pv("ArrayRate_RBV"): 1.0,
            _pv("Acquire"): 0,
            _pv("AcquireBusy"): "Done",
            IMAGE_PV: np.asarray(image, dtype=np.uint32),
        }
    )


@pytest.fixture
def fake_backend(monkeypatch):
    """Route all EPICS access for this module to one fake backend."""
    backend = FakeEpicsBackend()
    backend.close_subscription = lambda token: None
    monkeypatch.setattr(p4p, "P4pWrapper", lambda timeout: backend)
    monkeypatch.setattr(caproto, "CaprotoWrapper", lambda timeout: backend)
    _seed_backend(backend)
    return backend


def _create_channel(harness, name="camera"):
    """Create one master-mode image channel attached to the fake backend."""
    return harness.create_master(
        AreaDetector,
        name=name,
        pv_root=PV_ROOT,
        image_pv=IMAGE_PV,
        pva=True,
    )


def _create_collector(harness, name="ad_collector", image_names=("camera",)):
    """Create the aggregate detector that owns the image channel(s)."""
    return harness.create_master(
        AreaDetectorCollector,
        name=name,
        images=list(image_names),
    )


class TestAreaDetectorHarness:
    def test_explicit_image_preset_uses_active_channel_and_backend_completion(
        self, daemon_device_harness, fake_backend
    ):
        """The channel should behave like a real `ActiveChannel` controller.

        Setting a preset must store the preselection on the image channel, but
        completion still follows the backend busy/done state rather than the
        scalar image counter value.
        """
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness)

        assert isinstance(channel, ActiveChannel)

        collector.prepare()
        fake_backend.values[_pv("AcquireBusy")] = "Acquiring"
        # Use a deliberately unrelated counter value so the test shows that the
        # channel completes on backend status, not on the scalar readback.
        fake_backend.values[_pv("NumImagesCounter_RBV")] = 999
        collector.start(camera=IMAGE_PRESELECTION)

        try:
            assert channel.preselection == IMAGE_PRESELECTION
            assert fake_backend.values[_pv("Acquire")] == 1
            assert collector.isCompleted() is False

            fake_backend.values[_pv("AcquireBusy")] = "Done"
            assert collector.isCompleted() is True
        finally:
            collector.finish()

        assert fake_backend.values[_pv("Acquire")] == 0

    def test_channel_owned_arraydesc_drives_inherited_detector_array_reads(
        self, daemon_device_harness, fake_backend
    ):
        """The collector should reuse the channel's array metadata and image."""
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness)

        _seed_backend(
            fake_backend,
            shape=RESIZED_IMAGE_SHAPE,
            image=np.arange(np.prod(RESIZED_IMAGE_SHAPE), dtype=np.uint32),
        )
        collector.prepare()
        channel.get_image()

        assert channel.arrayInfo()[0].shape == RESIZED_IMAGE_SHAPE
        assert collector.arrayInfo()[0].shape == RESIZED_IMAGE_SHAPE
        np.testing.assert_array_equal(
            collector.readArrays(FINAL)[0],
            np.arange(np.prod(RESIZED_IMAGE_SHAPE), dtype=np.uint32).reshape(
                RESIZED_IMAGE_SHAPE
            ),
        )
