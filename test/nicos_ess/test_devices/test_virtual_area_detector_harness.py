import pytest

from nicos.core import InvalidValueError
from nicos.core.constants import FINAL
from nicos_ess.devices.virtual.area_detector import AreaDetector, AreaDetectorCollector
from test.nicos_ess.test_devices.doubles import wait_until_complete


def create_virtual_area_detector(daemon_device_harness):
    daemon_device_harness.session.updateLiveData = lambda *args, **kwargs: None
    image = daemon_device_harness.create_master(
        AreaDetector,
        name="virtual_camera",
        sizex=8,
        sizey=6,
        startx=0,
        starty=0,
        acquiretime=0.001,
        acquireperiod=0.01,
        numimages=1,
        imagemode="continuous",
        binning="1x1",
    )
    collector = daemon_device_harness.create_master(
        AreaDetectorCollector,
        name="virtual_collector",
        images=["virtual_camera"],
    )
    return image, collector


def test_virtual_area_detector_accepts_only_image_count_presets(
    daemon_device_harness,
):
    image, _collector = create_virtual_area_detector(daemon_device_harness)

    assert set(image.presetInfo()) == {"n"}

    image.setPreset(n=2)
    image.setPreset()
    assert image.preset() == {"n": 2}

    with pytest.raises(InvalidValueError):
        image.setPreset(t=1)


def test_virtual_area_detector_channel_preset_uses_image_counter_progress(
    daemon_device_harness,
):
    image, _collector = create_virtual_area_detector(daemon_device_harness)

    image.setChannelPreset("n", 2)

    assert image.iscontroller is True
    assert image.presetReached("n", 2, 0) is False

    image._ad_simulator._image_counter = 2
    assert image.presetReached("n", 2, 0) is True


def test_virtual_area_detector_collector_applies_image_preset_before_prepare(
    daemon_device_harness,
):
    image, collector = create_virtual_area_detector(daemon_device_harness)

    collector.setPreset(virtual_camera=2)

    assert image.preset() == {"n": 2}

    collector.prepare()
    assert image.preset() == {"n": 2}


def test_virtual_area_detector_collector_reuses_previous_image_preset(
    daemon_device_harness,
):
    image, collector = create_virtual_area_detector(daemon_device_harness)

    collector.setPreset(virtual_camera=2)
    collector.prepare()
    collector.setPreset()

    assert collector.preset() == {"virtual_camera": 2}
    assert image.preset() == {"n": 2}


def test_virtual_area_detector_collector_rejects_non_image_presets(
    daemon_device_harness,
):
    _image, collector = create_virtual_area_detector(daemon_device_harness)

    with pytest.raises(InvalidValueError):
        collector.setPreset(t=1)


def test_virtual_area_detector_collector_does_not_persist_live_as_previous_preset(
    daemon_device_harness,
):
    image, collector = create_virtual_area_detector(daemon_device_harness)

    collector.setPreset(virtual_camera=2)
    collector.setPreset(live=True)
    collector.setPreset()

    assert collector.preset() == {"virtual_camera": 2}
    assert image.preset() == {"n": 2}


def test_virtual_area_detector_collector_finishes_when_requested_image_count_is_reached(
    daemon_device_harness,
):
    image, collector = create_virtual_area_detector(daemon_device_harness)

    collector.setPreset(virtual_camera=2)
    collector.prepare()
    collector.start()
    wait_until_complete(collector, timeout=3.0)
    collector.finish()

    scalars, arrays = collector.readResults(FINAL)

    assert scalars == []
    assert image.read()[0] == 2
    assert len(arrays) == 1
    assert arrays[0].shape == image.arrayInfo()[0].shape


def test_virtual_area_detector_collector_preset_namespace_stays_image_only(
    daemon_device_harness,
):
    _image, collector = create_virtual_area_detector(daemon_device_harness)

    assert "virtual_camera" in collector.presetInfo()
    assert "t" not in collector.presetInfo()
