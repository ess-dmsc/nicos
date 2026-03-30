import numpy as np

from nicos.core import status
from nicos.core.constants import FINAL, INTERMEDIATE, LIVE
from nicos_ess.devices.virtual.area_detector import AreaDetector, AreaDetectorCollector
from test.nicos_ess.test_devices.doubles import wait_until_complete


def create_virtual_area_detector(daemon_device_harness, **collector_kwargs):
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
        **collector_kwargs,
    )
    return image, collector


def create_dual_virtual_area_detector_collector(daemon_device_harness):
    daemon_device_harness.session.updateLiveData = lambda *args, **kwargs: None
    primary = daemon_device_harness.create_master(
        AreaDetector,
        name="virtual_camera_primary",
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
    secondary = daemon_device_harness.create_master(
        AreaDetector,
        name="virtual_camera_secondary",
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
        images=["virtual_camera_primary", "virtual_camera_secondary"],
    )
    return primary, secondary, collector


class TestVirtualAreaDetectorHarness:
    def test_tracks_image_count_presets_and_ignores_unrelated_keys(
        self, daemon_device_harness
    ):
        image, _collector = create_virtual_area_detector(daemon_device_harness)

        assert set(image.presetInfo()) == {"n", "virtual_camera"}

        image.setPreset(n=2)
        image.setPreset(t=1)
        image.setPreset()
        assert image.preset() == {"n": 2}

    def test_channel_preset_uses_image_counter_progress(self, daemon_device_harness):
        image, _collector = create_virtual_area_detector(daemon_device_harness)

        image.setChannelPreset("n", 2)

        assert image.iscontroller is True
        assert image.preselection == 2
        assert image.presetReached("n", 2, 0) is False

        image._ad_simulator._image_counter = 2
        assert image.presetReached("n", 2, 0) is True


class TestVirtualAreaDetectorCollectorHarness:
    def test_applies_image_preset_before_prepare(self, daemon_device_harness):
        image, collector = create_virtual_area_detector(daemon_device_harness)

        collector.setPreset(virtual_camera=2)

        assert image.preset() == {"n": 2}

    def test_accepts_image_count_alias_from_underlying_channel(
        self, daemon_device_harness
    ):
        image, collector = create_virtual_area_detector(daemon_device_harness)

        collector.setPreset(n=2)

        assert collector.preset() == {"n": 2}
        assert image.preset() == {"n": 2}

        collector.prepare()
        assert image.preset() == {"n": 2}

    def test_reuses_previous_image_preset(self, daemon_device_harness):
        image, collector = create_virtual_area_detector(daemon_device_harness)

        collector.setPreset(virtual_camera=2)
        collector.prepare()
        collector.setPreset()

        assert collector.preset() == {"virtual_camera": 2}
        assert image.preset() == {"n": 2}

    def test_ignores_non_image_presets(self, daemon_device_harness):
        image, collector = create_virtual_area_detector(daemon_device_harness)

        collector.setPreset(virtual_camera=2)
        collector.setPreset(t=1)

        assert collector.preset() == {"virtual_camera": 2}
        assert image.preset() == {"n": 2}

    def test_does_not_persist_live_as_previous_preset(self, daemon_device_harness):
        image, collector = create_virtual_area_detector(daemon_device_harness)

        collector.setPreset(virtual_camera=2)
        collector.setPreset(live=True)
        collector.setPreset()

        assert collector.preset() == {"virtual_camera": 2}
        assert image.preset() == {"n": 2}

    def test_prepare_leaves_collector_ready_until_start(self, daemon_device_harness):
        _image, collector = create_virtual_area_detector(daemon_device_harness)

        collector.setPreset(virtual_camera=1)
        collector.prepare()

        assert collector.isCompleted() is True

    def test_during_measure_hook_supports_intermediate_saveintervals(
        self, daemon_device_harness
    ):
        _image, collector = create_virtual_area_detector(
            daemon_device_harness,
            liveinterval=1.0,
            saveintervals=[0.2],
        )

        collector.prepare()
        collector.start()

        assert collector.duringMeasureHook(0.05) == LIVE
        assert collector.duringMeasureHook(0.25) == INTERMEDIATE
        assert collector.duringMeasureHook(1.1) == LIVE

        collector.finish()

    def test_pause_reports_unsupported_and_resume_is_noop(
        self, daemon_device_harness
    ):
        _image, collector = create_virtual_area_detector(daemon_device_harness)

        collector.setPreset(virtual_camera=1)
        collector.prepare()
        collector.start()

        assert collector.pause() is False
        collector.resume()

        collector.finish()

    def test_finishes_when_requested_image_count_is_reached(
        self, daemon_device_harness
    ):
        image, collector = create_virtual_area_detector(daemon_device_harness)

        collector.setPreset(virtual_camera=2)
        collector.prepare()
        collector.start()
        wait_until_complete(collector, timeout=3.0)
        collector.finish()

        scalars, arrays = collector.readResults(FINAL)

        assert scalars == [2]
        assert image.read()[0] == 2
        assert len(arrays) == 1
        assert arrays[0].shape == image.arrayInfo()[0].shape

    def test_completion_syncs_final_image_before_collector_reports_done(
        self, daemon_device_harness
    ):
        image, collector = create_virtual_area_detector(daemon_device_harness)
        final_shape = image.arrayInfo()[0].shape
        final_image = np.arange(np.prod(final_shape), dtype=np.uint16).reshape(
            final_shape
        )

        collector.setPreset(virtual_camera=2)
        collector.prepare()
        image._setROParam("curstatus", (status.BUSY, "Acquiring"))
        image._ad_simulator._image = final_image.ravel()
        image._ad_simulator._image_counter = 2

        assert not np.array_equal(image.readArray(FINAL), final_image)
        assert collector.isCompleted() is False

        image._setROParam("curstatus", (status.OK, "Done"))
        assert collector.isCompleted() is True

        _scalars, arrays = collector.readResults(FINAL)

        assert len(arrays) == 1
        assert np.array_equal(arrays[0], final_image)

    def test_completion_matches_generic_detector_or_semantics(
        self, daemon_device_harness
    ):
        primary, secondary, collector = create_dual_virtual_area_detector_collector(
            daemon_device_harness
        )
        final_shape = primary.arrayInfo()[0].shape
        final_image = np.arange(np.prod(final_shape), dtype=np.uint16).reshape(
            final_shape
        )

        collector.setPreset(virtual_camera_primary=1, virtual_camera_secondary=3)
        collector.prepare()
        primary._setROParam("curstatus", (status.OK, "Done"))
        primary._ad_simulator._image = final_image.ravel()
        primary._ad_simulator._image_counter = 1
        secondary._setROParam("curstatus", (status.BUSY, "Acquiring"))
        secondary._ad_simulator._image_counter = 0

        assert collector.isCompleted() is True
        assert np.array_equal(primary.readArray(FINAL), final_image)

    def test_preset_namespace_stays_image_only(self, daemon_device_harness):
        _image, collector = create_virtual_area_detector(daemon_device_harness)

        assert "n" in collector.presetInfo()
        assert "virtual_camera" in collector.presetInfo()
        assert "t" not in collector.presetInfo()
