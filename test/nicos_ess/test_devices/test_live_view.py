"""The live view sink that sends clients reduced images."""

import time
from types import SimpleNamespace

import numpy
import pytest

from nicos_ess.devices.datasinks.live_view import ReducedLiveViewSinkHandler

session_setup = None


@pytest.fixture(autouse=True)
def experiment(session, monkeypatch):
    # The handler constructor reads the data manager of the experiment.
    monkeypatch.setattr(session, "_experiment", SimpleNamespace(data=None))


def make_handler(maxpoints=512 * 512):
    sink = SimpleNamespace(maxpoints=maxpoints, log=None)
    dataset = SimpleNamespace(uid="uid", started=0)
    detector = SimpleNamespace(name="det")
    return ReducedLiveViewSinkHandler(sink, dataset, detector)


def put(handler, *arrays):
    handler.putResults("live", {"det": ([], list(arrays))})


def test_a_camera_frame_is_reduced(live_updates):
    rng = numpy.random.default_rng(0)
    frame = rng.poisson(1000, size=(2048, 2048)).astype(numpy.uint16)

    put(make_handler(), frame)

    ((params, blobs, _labels),) = live_updates
    desc = params["datadescs"][0]
    assert desc["shape"] == (512, 512)
    received = numpy.frombuffer(blobs[0], desc["dtype"]).reshape(512, 512)
    expected = frame.reshape(512, 4, 512, 4).mean(axis=(1, 3))  # not counts
    numpy.testing.assert_allclose(received, expected)


def test_the_axes_keep_counting_sensor_pixels(live_updates):
    put(make_handler(), numpy.zeros((2048, 1024), numpy.uint16))

    labels = live_updates[0][0]["datadescs"][0]["labels"]
    assert labels["x"] == dict(define="range", start=0.5, step=2, length=512, title="x")
    assert labels["y"] == dict(define="range", start=1.5, step=4, length=512, title="y")


def test_small_images_and_spectra_keep_their_shape_and_values(live_updates):
    image = numpy.arange(12, dtype=numpy.uint16).reshape(3, 4)
    spectrum = numpy.arange(5000, dtype=numpy.int32)

    put(make_handler(), image, spectrum)

    params, blobs, _labels = live_updates[0]
    descs = params["datadescs"]
    assert [d["shape"] for d in descs] == [(3, 4), (5000,)]
    received = numpy.frombuffer(blobs[0], descs[0]["dtype"]).reshape(3, 4)
    numpy.testing.assert_array_equal(received, image)


def test_the_event_time_counts_from_the_start_of_the_count(live_updates):
    handler = make_handler()
    handler.dataset.started = time.time() - 5

    put(handler, numpy.zeros((2, 2)))

    assert live_updates[0][0]["time"] == pytest.approx(5, abs=1)


def test_missing_arrays_are_skipped(live_updates):
    put(make_handler(), None)

    assert live_updates == []
