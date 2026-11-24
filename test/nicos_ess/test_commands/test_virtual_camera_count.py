"""Tests of the simulated camera as an image channel of a stock NICOS Detector."""

import threading
import time

import numpy
import pytest

from nicos.commands.measure import count
from nicos.core import FINAL
from nicos.devices.generic import Detector
from nicos_ess.devices.virtual.area_detector import AreaDetector
from test.nicos_ess.command_helpers import loaded_setup, set_detectors, wait_until

session_setup = None

SIZE_X = 64
SIZE_Y = 32


@pytest.fixture
def camera(session):
    with loaded_setup(session, "ess_virtual_camera_count"):
        set_detectors(session, "det")
        camera = session.getDevice("cam")
        # The adcore setups also have a device called cam, and the test cache
        # keeps parameters by device name, so every input is set here.
        camera.sizex = SIZE_X
        camera.sizey = SIZE_Y
        camera.startx = 0
        camera.starty = 0
        camera.binning = "1x1"
        camera.acquiretime = 0.1
        camera.acquireperiod = 0.02
        yield camera


def test_the_preset_gives_the_number_of_images(camera, live_updates):
    result = count(cam=3)

    assert result[-1] == 3


def test_a_preset_of_one_takes_a_single_image(camera, live_updates):
    result = count(cam=1)

    assert result[-1] == 1


def test_the_image_reaches_the_live_view_through_the_detector(camera, live_updates):
    count(cam=2)

    received = live_updates.frames()
    assert received
    assert {det for det, _frame in received} == {"det"}
    _det, last = received[-1]
    assert last.dims == ("y", "x")
    assert last.binned == {}
    numpy.testing.assert_array_equal(last.data, camera.readArray(FINAL))


def test_the_live_view_sends_the_image_in_the_smallest_type(camera, live_updates):
    count(cam=1)

    _det, last = live_updates.frames()[-1]
    # With an exposure of 0.1 s the simulated pixels stay below 255.
    assert camera.readArray(FINAL).dtype == numpy.uint16
    assert last.data.dtype == numpy.uint8


def test_binning_shrinks_the_read_array(camera, live_updates):
    camera.binning = "2x2"
    count(cam=1)

    assert camera.readArray(FINAL).shape == (SIZE_Y // 2, SIZE_X // 2)


def test_binning_shrinks_the_array_info(camera, live_updates):
    camera.binning = "2x2"

    assert camera.arrayInfo()[0].shape == (SIZE_Y // 2, SIZE_X // 2)


def make_camera(device_harness, **config):
    """Create the camera and its detector on an empty cache."""
    camera = device_harness.create_daemon(
        AreaDetector, name="vcam", acquireperiod=0.01, **config
    )
    detector = device_harness.create_daemon(Detector, name="vdet", images=["vcam"])
    return camera, detector


def count_images(device_harness, detector, images):
    with device_harness.activate("daemon"):
        detector.setPreset(vcam=images)
        detector.prepare()
        detector.start()
        assert wait_until(detector.isCompleted, timeout=1)
        detector.finish()
        return detector.readArrays(FINAL)[0]


def test_a_fresh_camera_uses_its_configured_settings(device_harness):
    camera, detector = make_camera(device_harness, sizex=SIZE_X, sizey=SIZE_Y)

    assert (camera.sizex, camera.sizey, camera.acquireperiod) == (SIZE_X, SIZE_Y, 0.01)
    assert count_images(device_harness, detector, 2).shape == (SIZE_Y, SIZE_X)


@pytest.mark.parametrize(
    "roi, shape",
    [
        (dict(sizex=33, sizey=SIZE_Y, binning="2x2"), (SIZE_Y // 2, 16)),
        (dict(startx=1000, sizex=SIZE_X, sizey=SIZE_Y), (SIZE_Y, 24)),
        (dict(startx=-5, sizex=2000, sizey=SIZE_Y, binning="4x4"), (SIZE_Y // 4, 256)),
    ],
)
def test_the_roi_is_cut_to_the_sensor_and_to_whole_bins(device_harness, roi, shape):
    camera, detector = make_camera(device_harness, **roi)

    assert count_images(device_harness, detector, 2).shape == shape
    assert camera.arrayInfo()[0].shape == shape
    # Like an ADCore setpoint, the parameter keeps the requested region.
    assert camera.sizex == roi["sizex"]


def test_a_stop_during_the_period_takes_no_more_image(device_harness):
    camera = make_camera(device_harness)[0]

    with device_harness.activate("daemon"):
        camera.acquireperiod = 0.2
        camera.start()
        camera.stop()
        time.sleep(0.4)
        assert camera.read() == [0]


def test_a_restart_during_an_image_drops_that_image(device_harness, monkeypatch):
    camera = make_camera(device_harness)[0]
    in_image = threading.Event()
    release = threading.Event()
    region = AreaDetector.region

    def slow_region(device):
        in_image.set()
        release.wait(1)
        return region(device)

    monkeypatch.setattr(AreaDetector, "region", slow_region)
    with device_harness.activate("daemon"):
        camera.start()
        assert in_image.wait(1)
        camera.acquireperiod = 1
        camera.stop()
        camera.start()
        release.set()
        time.sleep(0.2)
        assert camera.read() == [0]
