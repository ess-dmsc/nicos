import numpy as np
import pytest

from nicos.core import ArrayDesc, status
from nicos.devices.epics.pva import caproto, p4p
from nicos_ess.devices.epics.area_detector import AreaDetector, AreaDetectorCollector
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend


PV_ROOT = "SIM:AD:"
IMAGE_PV = "SIM:AD:IMAGE"


def seed_area_detector_defaults(fake_backend, pv_root=PV_ROOT, image_pv=IMAGE_PV):
    fake_backend.values.update(
        {
            f"{pv_root}MaxSizeX_RBV": 1024,
            f"{pv_root}MaxSizeY_RBV": 2048,
            f"{pv_root}DataType_RBV": "UInt32",
            f"{pv_root}NumImagesCounter_RBV": 0,
            f"{pv_root}DetectorState_RBV": 0,
            f"{pv_root}DetectorState_RBV.STAT": 0,
            f"{pv_root}DetectorState_RBV.SEVR": 0,
            f"{pv_root}ArrayRate_RBV": 0,
            f"{pv_root}Acquire": 0,
            f"{pv_root}AcquireBusy": "Done",
            image_pv: np.zeros((2048, 1024), dtype=np.uint32).ravel(),
        }
    )


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()
    monkeypatch.setattr(p4p, "P4pWrapper", lambda timeout=3.0, context=None: backend)
    monkeypatch.setattr(caproto, "CaprotoWrapper", lambda timeout=3.0: backend)
    seed_area_detector_defaults(backend)
    return backend


def create_area_detector(daemon_device_harness):
    return daemon_device_harness.create_master(
        AreaDetector,
        name="ad_1",
        pv_root=PV_ROOT,
        image_pv=IMAGE_PV,
    )


def test_area_detector_array_info_returns_tuple_of_arraydesc(
    daemon_device_harness, fake_backend
):
    del fake_backend
    detector = create_area_detector(daemon_device_harness)

    info = detector.arrayInfo()

    assert isinstance(info, tuple)
    assert isinstance(info[0], ArrayDesc)


def test_area_detector_completed_reflects_acquire_status(
    daemon_device_harness, fake_backend
):
    detector = create_area_detector(daemon_device_harness)

    fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Done"
    assert detector.isCompleted() is True

    fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Busybusybusy"
    assert detector.isCompleted() is False


def test_area_detector_tracks_image_count_presets_and_ignores_unrelated_keys(
    daemon_device_harness, fake_backend
):
    del fake_backend
    detector = create_area_detector(daemon_device_harness)

    assert set(detector.presetInfo()) == {"n"}

    detector.setPreset(n=3)
    detector.setPreset(t=1)
    detector.setPreset()
    assert detector.preset() == {"n": 3}


def test_area_detector_channel_preset_uses_image_counter_progress(
    daemon_device_harness, fake_backend
):
    detector = create_area_detector(daemon_device_harness)

    detector.setChannelPreset("n", 2)

    fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 1
    assert detector.iscontroller is True
    assert detector.presetReached("n", 2, 0) is False

    fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 2
    assert detector.presetReached("n", 2, 0) is True


def test_area_detector_start_marks_device_busy(daemon_device_harness, fake_backend):
    detector = create_area_detector(daemon_device_harness)

    detector.start(n=1)

    assert detector._current_status == (status.BUSY, "Acquiring")
    assert fake_backend.values[f"{PV_ROOT}Acquire"] == 1


def test_area_detector_completes_on_image_count_preset_before_backend_status(
    daemon_device_harness, fake_backend
):
    detector = create_area_detector(daemon_device_harness)

    fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Busybusybusy"
    detector.start(n=2)
    fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 1
    assert detector.isCompleted() is False

    fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 2
    assert detector.isCompleted() is True


def test_area_detector_collector_uses_image_presets_and_ignores_unrelated_ones(
    daemon_device_harness, fake_backend
):
    del fake_backend
    image = daemon_device_harness.create_master(
        AreaDetector,
        name="camera",
        pv_root=PV_ROOT,
        image_pv=IMAGE_PV,
    )
    collector = daemon_device_harness.create_master(
        AreaDetectorCollector,
        name="collector",
        images=["camera"],
    )

    assert collector.valueInfo() == ()
    assert "camera" in collector.presetInfo()
    assert "t" not in collector.presetInfo()

    collector.setPreset(camera=4)
    assert image.preset() == {"n": 4}

    collector.prepare()
    collector.setPreset(t=1)
    collector.setPreset()
    assert collector.preset() == {"camera": 4}
    assert image.preset() == {"n": 4}


def test_area_detector_collector_does_not_persist_live_as_previous_preset(
    daemon_device_harness, fake_backend
):
    del fake_backend
    image = daemon_device_harness.create_master(
        AreaDetector,
        name="camera",
        pv_root=PV_ROOT,
        image_pv=IMAGE_PV,
    )
    collector = daemon_device_harness.create_master(
        AreaDetectorCollector,
        name="collector",
        images=["camera"],
    )

    collector.setPreset(camera=4)
    collector.setPreset(live=True)
    collector.setPreset()

    assert collector.preset() == {"camera": 4}
    assert image.preset() == {"n": 4}
