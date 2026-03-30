import threading
import time

import numpy as np
import pytest

from nicos.core import ArrayDesc, status
from nicos.core.constants import FINAL, INTERMEDIATE, LIVE

from nicos_ess.devices.datasources import just_bin_it
from nicos_ess.devices.kafka import status_handler
from nicos_ess.devices.timer import TimerChannel
from test.nicos_ess.test_devices.doubles import (
    StubKafkaProducer,
    patch_kafka_stubs,
    wait_until_complete,
)


@pytest.fixture
def kafka_stubs(monkeypatch):
    producer = StubKafkaProducer()

    def immediate_ack(self, identifier, timeout_duration):
        del self, identifier, timeout_duration

    patch_kafka_stubs(
        monkeypatch,
        just_bin_it,
        producer=producer,
        status_module=status_handler,
    )
    monkeypatch.setattr(
        just_bin_it.JustBinItDetector,
        "_check_for_ack",
        immediate_ack,
    )
    return producer


def create_image(daemon_device_harness):
    return daemon_device_harness.create_master(
        just_bin_it.JustBinItImage,
        name="jbi_image",
        brokers=["localhost:9092"],
        hist_topic="jbi_hist",
        data_topic="jbi_data",
    )


def create_named_image(daemon_device_harness, name):
    return daemon_device_harness.create_master(
        just_bin_it.JustBinItImage,
        name=name,
        brokers=["localhost:9092"],
        hist_topic=f"{name}_hist",
        data_topic=f"{name}_data",
    )


def create_detector(daemon_device_harness, include_timer, **detector_overrides):
    image = create_image(daemon_device_harness)
    detector_kwargs = {
        "brokers": ["localhost:9092"],
        "command_topic": "jbi_command",
        "response_topic": "jbi_response",
        "statustopic": [],
        "images": ["jbi_image"],
        "liveinterval": 0.5,
    }
    detector_kwargs.update(detector_overrides)
    if include_timer:
        timer = daemon_device_harness.create_master(
            TimerChannel,
            name="timer",
            update_interval=0.01,
        )
        detector_kwargs["timers"] = ["timer"]
    else:
        timer = None
    detector = daemon_device_harness.create_master(
        just_bin_it.JustBinItDetector,
        name="jbi_detector",
        **detector_kwargs,
    )
    return image, timer, detector


def create_multi_image_detector(
    daemon_device_harness, image_names, include_timer=False, **detector_overrides
):
    images = [create_named_image(daemon_device_harness, name) for name in image_names]
    detector_kwargs = {
        "brokers": ["localhost:9092"],
        "command_topic": "jbi_command",
        "response_topic": "jbi_response",
        "statustopic": [],
        "images": [image.name for image in images],
        "liveinterval": 0.5,
    }
    detector_kwargs.update(detector_overrides)
    if include_timer:
        timer = daemon_device_harness.create_master(
            TimerChannel,
            name="timer",
            update_interval=0.01,
        )
        detector_kwargs["timers"] = ["timer"]
    else:
        timer = None
    detector = daemon_device_harness.create_master(
        just_bin_it.JustBinItDetector,
        name="jbi_detector",
        **detector_kwargs,
    )
    return images, timer, detector


def push_image_sum(image, total, delay=0.05):
    def _update():
        time.sleep(delay)
        image._hist_data = np.full((image.num_bins,), total / image.num_bins)
        image._hist_sum = total
        image._current_status = (status.BUSY, "Counting")

    thread = threading.Thread(target=_update, daemon=True)
    thread.start()
    return thread


def stop_messages(producer):
    return [
        message
        for message in producer.messages
        if message["message"] == b'{"cmd": "stop"}'
    ]


class TestJustBinItImageHarness:
    def test_array_info_returns_tuple_of_arraydescs(
        self, daemon_device_harness, kafka_stubs
    ):
        del kafka_stubs
        image = create_image(daemon_device_harness)

        info = image.arrayInfo()

        assert isinstance(info, tuple)
        assert len(info) == 1
        assert isinstance(info[0], ArrayDesc)


class TestJustBinItDetectorHarness:
    def test_array_info_flattens_attached_image_descriptors(
        self, daemon_device_harness, kafka_stubs
    ):
        del kafka_stubs
        _image, _timer, detector = create_detector(daemon_device_harness, False)

        info = detector.arrayInfo()

        assert isinstance(info, tuple)
        assert len(info) == 1
        assert isinstance(info[0], ArrayDesc)

    @pytest.mark.parametrize("terminator", ["finish", "stop"])
    def test_timer_preset_stops_histogram_once(
        self, daemon_device_harness, kafka_stubs, terminator
    ):
        _image, _timer, detector = create_detector(daemon_device_harness, True)

        detector.setPreset(t=0.05)
        detector.prepare()
        detector.start()
        assert detector.duringMeasureHook(0.6) == LIVE
        wait_until_complete(detector)

        assert len(stop_messages(kafka_stubs)) == 0

        getattr(detector, terminator)()
        _scalars, arrays = detector.readResults(FINAL)

        assert len(stop_messages(kafka_stubs)) == 1
        assert len(arrays) == 1

    def test_image_preset_stops_when_image_count_reaches_target_without_duplicate_stop(
        self, daemon_device_harness, kafka_stubs
    ):
        image, _timer, detector = create_detector(daemon_device_harness, False)

        detector.setPreset(jbi_image=5)
        detector.prepare()
        detector.start()
        push_image_sum(image, 5)
        wait_until_complete(detector)

        assert len(stop_messages(kafka_stubs)) == 0

        detector.finish()

        assert image.read()[0] == 5
        assert len(stop_messages(kafka_stubs)) == 1

    def test_mixed_timer_and_image_presets_complete_on_first_controller(
        self, daemon_device_harness, kafka_stubs
    ):
        image, timer, detector = create_detector(daemon_device_harness, True)

        detector.setPreset(t=0.5, jbi_image=5)
        detector.prepare()
        detector.start()
        push_image_sum(image, 5)
        wait_until_complete(detector)
        detector.finish()

        assert image.read()[0] == 5
        assert timer.read()[0] < 0.5
        assert len(stop_messages(kafka_stubs)) == 1

    def test_multiple_image_presets_complete_on_first_reached_image_controller(
        self, daemon_device_harness, kafka_stubs
    ):
        images, _timer, detector = create_multi_image_detector(
            daemon_device_harness,
            ["jbi_image_fast", "jbi_image_slow"],
        )
        fast_image, slow_image = images

        detector.setPreset(jbi_image_fast=5, jbi_image_slow=9)
        detector.prepare()
        detector.start()
        push_image_sum(fast_image, 5)
        wait_until_complete(detector)

        assert tuple(ch.name for ch in detector._controlchannels) == (
            "jbi_image_fast",
            "jbi_image_slow",
        )
        assert fast_image.read()[0] == 5
        assert slow_image.read()[0] == 0
        assert len(stop_messages(kafka_stubs)) == 0

        detector.finish()
        _scalars, arrays = detector.readResults(FINAL)

        assert len(arrays) == 2
        assert len(stop_messages(kafka_stubs)) == 1

    def test_during_measure_hook_supports_intermediate_saveintervals(
        self, daemon_device_harness, kafka_stubs
    ):
        _image, _timer, detector = create_detector(
            daemon_device_harness,
            False,
            liveinterval=1.0,
            saveintervals=[0.2],
        )

        detector.prepare()
        detector.start()

        assert detector.duringMeasureHook(0.05) == LIVE
        assert detector.duringMeasureHook(0.25) == INTERMEDIATE
        assert detector.duringMeasureHook(1.1) == LIVE

        detector.finish()

    def test_pause_reports_unsupported_and_resume_is_noop(
        self, daemon_device_harness, kafka_stubs
    ):
        _image, _timer, detector = create_detector(daemon_device_harness, False)

        detector.setPreset(jbi_image=5)
        detector.prepare()
        detector.start()

        assert detector.pause() is False
        detector.resume()

        detector.finish()
