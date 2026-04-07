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


def _pv(suffix):
    return f"{PV_ROOT}{suffix}"


def _seed_backend(backend, *, shape=(3, 4), image=None):
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
    backend = FakeEpicsBackend()
    backend.close_subscription = lambda token: None
    monkeypatch.setattr(p4p, "P4pWrapper", lambda timeout: backend)
    monkeypatch.setattr(caproto, "CaprotoWrapper", lambda timeout: backend)
    _seed_backend(backend)
    return backend


def _create_channel(harness, name="camera"):
    return harness.create_master(
        AreaDetector,
        name=name,
        pv_root=PV_ROOT,
        image_pv=IMAGE_PV,
        pva=True,
    )


def _create_collector(harness, name="ad_collector", image_names=("camera",)):
    return harness.create_master(
        AreaDetectorCollector,
        name=name,
        images=list(image_names),
    )


def _create_channel_pair(device_harness, name="camera"):
    return device_harness.create_pair(
        AreaDetector,
        name=name,
        shared={
            "pv_root": PV_ROOT,
            "image_pv": IMAGE_PV,
            "pva": True,
        },
    )


def _create_collector_pair(
    device_harness, name="ad_collector", image_names=("camera",)
):
    return device_harness.create_pair(
        AreaDetectorCollector,
        name=name,
        shared={"images": list(image_names)},
    )


class TestAreaDetectorHarness:
    def test_initializes_channel_and_collector_in_both_roles(
        self, device_harness, fake_backend
    ):
        daemon_channel, poller_channel = _create_channel_pair(device_harness)
        daemon_collector, poller_collector = _create_collector_pair(device_harness)

        daemon_shape = device_harness.run_daemon(
            lambda: daemon_channel.arrayInfo()[0].shape
        )
        poller_shape = device_harness.run_poller(
            lambda: poller_channel.arrayInfo()[0].shape
        )
        assert daemon_shape == (3, 4)
        assert poller_shape == (3, 4)

    def test_explicit_image_preset_uses_active_channel_and_backend_completion(
        self, daemon_device_harness, fake_backend
    ):
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness)

        assert isinstance(channel, ActiveChannel)

        collector.prepare()
        fake_backend.values[_pv("AcquireBusy")] = "Acquiring"
        fake_backend.values[_pv("NumImagesCounter_RBV")] = 999
        collector.start(camera=5)

        try:
            assert channel.preselection == 5
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
        channel = _create_channel(daemon_device_harness)
        collector = _create_collector(daemon_device_harness)

        _seed_backend(fake_backend, shape=(2, 6), image=np.arange(12, dtype=np.uint32))
        collector.prepare()
        channel.get_image()

        assert channel.arrayInfo()[0].shape == (2, 6)
        assert collector.arrayInfo()[0].shape == (2, 6)
        np.testing.assert_array_equal(
            collector.readArrays(FINAL)[0],
            np.arange(12, dtype=np.uint32).reshape(2, 6),
        )
