# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

import threading
import time

import numpy as np
import pytest

from nicos.core import ArrayDesc, status
from nicos.core.constants import FINAL, LIVE

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
        del identifier, timeout_duration
        if self._conditions:
            self._conditions_thread = just_bin_it.createThread(
                "jbi-conditions",
                self._check_conditions,
                (self._conditions.copy(),),
            )

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


def create_detector(daemon_device_harness, include_timer):
    image = create_image(daemon_device_harness)
    detector_kwargs = {
        "brokers": ["localhost:9092"],
        "command_topic": "jbi_command",
        "response_topic": "jbi_response",
        "statustopic": [],
        "images": ["jbi_image"],
        "liveinterval": 0.5,
    }
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
