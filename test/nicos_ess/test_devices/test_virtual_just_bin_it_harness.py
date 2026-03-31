import numpy as np

from nicos.core.constants import FINAL
from nicos_ess.devices.virtual import just_bin_it
from nicos_ess.devices.timer import TimerChannel
from test.nicos_ess.test_devices.doubles import wait_for, wait_until_complete


def create_image(daemon_device_harness, name, **overrides):
    image_kwargs = {
        "name": name,
        "brokers": ["localhost:9092"],
        "hist_topic": f"{name}_hist",
        "data_topic": f"{name}_data",
        "hist_type": "1-D TOF",
        "num_bins": 8,
    }
    image_kwargs.update(overrides)
    return daemon_device_harness.create_master(
        just_bin_it.JustBinItImage,
        **image_kwargs,
    )


def create_detector(
    daemon_device_harness,
    image_names,
    *,
    include_timer=False,
    **detector_overrides,
):
    daemon_device_harness.session.updateLiveData = lambda *args, **kwargs: None
    images = [create_image(daemon_device_harness, name) for name in image_names]
    detector_kwargs = {
        "name": "sim_jbi_detector",
        "brokers": ["localhost:9092"],
        "command_topic": "jbi_command",
        "response_topic": "jbi_response",
        "statustopic": [],
        "images": [image.name for image in images],
        "liveinterval": 0.5,
    }
    if include_timer:
        timer = daemon_device_harness.create_master(
            TimerChannel,
            name="sim_timer",
            update_interval=0.01,
        )
        detector_kwargs["timers"] = ["sim_timer"]
    else:
        timer = None
    detector_kwargs.update(detector_overrides)
    detector = daemon_device_harness.create_master(
        just_bin_it.JustBinItDetector,
        **detector_kwargs,
    )
    return images, timer, detector


class TestVirtualJustBinItImageHarness:
    def test_daemon_and_poller_share_counter_via_cache(self, device_harness):
        daemon_image, poller_image = device_harness.create_pair(
            just_bin_it.JustBinItImage,
            name="jbi_image",
            shared={
                "brokers": ["localhost:9092"],
                "hist_topic": "jbi_image_hist",
                "data_topic": "jbi_image_data",
                "hist_type": "1-D TOF",
                "num_bins": 8,
            },
        )
        daemon_detector, _poller_detector = device_harness.create_pair(
            just_bin_it.JustBinItDetector,
            name="jbi_detector",
            shared={
                "brokers": ["localhost:9092"],
                "command_topic": "jbi_command",
                "response_topic": "jbi_response",
                "statustopic": [],
                "images": ["jbi_image"],
                "liveinterval": 0.5,
            },
        )

        device_harness.run_daemon(daemon_detector.setPreset, jbi_image=5)
        device_harness.run_daemon(daemon_detector.prepare)
        device_harness.run_daemon(daemon_detector.start)
        device_harness.run_daemon(wait_until_complete, daemon_detector, timeout=3.0)
        device_harness.run_daemon(daemon_detector.finish)

        daemon_total = device_harness.run_daemon(lambda: daemon_image.read()[0])
        wait_for(
            lambda: device_harness.run_poller(lambda: poller_image.read()[0])
            == daemon_total,
            timeout=2.0,
        )

        assert daemon_total >= 5
        assert device_harness.run_poller(lambda: poller_image.read()[0]) == daemon_total


class TestVirtualJustBinItDetectorHarness:
    def test_timer_preset_counts_locally_and_returns_arrays(
        self, daemon_device_harness
    ):
        [image], _timer, detector = create_detector(
            daemon_device_harness,
            ["jbi_image"],
            include_timer=True,
        )

        detector.setPreset(t=0.3)
        detector.prepare()
        detector.start()
        wait_until_complete(detector, timeout=3.0)
        detector.finish()

        scalars, arrays = detector.readResults(FINAL)

        assert scalars[0] >= 0.3
        assert image.read()[0] > 0
        assert len(arrays) == 1
        assert arrays[0].shape == image.arrayInfo()[0].shape

    def test_multiple_image_presets_complete_on_first_reached_controller(
        self, daemon_device_harness
    ):
        images, _timer, detector = create_detector(
            daemon_device_harness,
            ["jbi_image_fast", "jbi_image_slow"],
        )
        fast_image, slow_image = images
        slow_target = 1_000_000

        detector.setPreset(jbi_image_fast=5, jbi_image_slow=slow_target)
        detector.prepare()
        detector.start()
        wait_until_complete(detector, timeout=3.0)
        slow_value_before_finish = slow_image.read()[0]
        detector.finish()

        assert tuple(ch.name for ch in detector._controlchannels) == (
            "jbi_image_fast",
            "jbi_image_slow",
        )
        assert fast_image.read()[0] >= 5
        assert slow_value_before_finish < slow_target

    def test_shape_updates_when_histogram_config_changes_mid_run(
        self, daemon_device_harness
    ):
        [image], _timer, detector = create_detector(
            daemon_device_harness,
            ["jbi_image"],
        )

        detector.prepare()
        detector.start()
        wait_for(lambda: image.read()[0] > 0, timeout=2.0)

        assert image.arrayInfo()[0].shape == (8,)

        image.num_bins = 12
        wait_for(
            lambda: image.arrayInfo()[0].shape == (12,)
            and image.readArray(FINAL).shape == (12,),
            timeout=2.0,
        )
        detector.stop()

        assert np.asarray(image.readArray(FINAL)).shape == (12,)
