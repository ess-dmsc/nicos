"""Tests of the simulated camera as an image channel of a stock NICOS Detector."""

import numpy
import pytest

from nicos.commands.measure import count
from nicos.core import FINAL
from test.nicos_ess.command_helpers import loaded_setup, set_detectors

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
