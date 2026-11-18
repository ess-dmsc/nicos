"""Tests for the live view sink that sends reduced, self-describing frames."""

import logging
import time
from types import SimpleNamespace

import numpy
import pytest

from nicos.core.params import ArrayDesc
from nicos_ess.devices.datasinks.live_view import ReducedLiveViewSinkHandler
from nicos_ess.utilities.live_frame import Coord, LiveArrayDesc, decode

session_setup = None


@pytest.fixture(autouse=True)
def experiment(session, monkeypatch):
    # The handler constructor reads the data manager of the experiment.
    monkeypatch.setattr(session, "_experiment", SimpleNamespace(data=None))


def make_handler(maxpoints=512 * 512, descs=None):
    sink = SimpleNamespace(maxpoints=maxpoints, log=logging.getLogger("live_view"))
    dataset = SimpleNamespace(uid="uid", started=0)
    detector = SimpleNamespace(name="det", arrayInfo=lambda: descs or ())
    return ReducedLiveViewSinkHandler(sink, dataset, detector)


HITS = [LiveArrayDesc("cam", (2048, 2048), "u2", "yx", counts=True)]


def put(handler, *arrays):
    handler.putResults("live", {"det": ([], list(arrays))})


def test_a_camera_frame_is_reduced(live_updates):
    rng = numpy.random.default_rng(0)
    frame = rng.poisson(1000, size=(2048, 2048)).astype(numpy.uint16)

    put(make_handler(descs=HITS), frame)

    ((params, blobs, _labels),) = live_updates
    desc = params["datadescs"][0]
    assert desc["shape"] == (512, 512)
    assert desc["dtype"] == numpy.dtype(numpy.uint16).str
    assert len(blobs[0]) == 512 * 512 * 2
    received = numpy.frombuffer(blobs[0], desc["dtype"]).reshape(512, 512)
    assert received.sum() == frame.sum()
    assert desc["frame"]["meta"] == {}


def test_saturated_pixels_are_counted_before_bins_are_combined(live_updates):
    frame = numpy.full((2048, 2048), 1000, numpy.uint16)
    frame[:2, :3] = 65535

    # The 4x4 blocks hide the saturated pixels, so meta keeps their number.
    put(make_handler(descs=HITS), frame)

    assert live_updates[0][0]["datadescs"][0]["frame"]["meta"] == {"saturated": 6}


def test_small_images_and_spectra_keep_their_shape_and_values(live_updates):
    image = numpy.arange(12, dtype=numpy.uint16).reshape(3, 4)
    spectrum = numpy.arange(5000, dtype=numpy.int32)

    put(make_handler(), image, spectrum)

    params, blobs, _labels = live_updates[0]
    descs = params["datadescs"]
    assert [d["shape"] for d in descs] == [(3, 4), (5000,)]
    received = numpy.frombuffer(blobs[0], descs[0]["dtype"]).reshape(3, 4)
    numpy.testing.assert_array_equal(received, image)
    assert descs[0]["dtype"] == numpy.dtype(numpy.uint8).str
    assert descs[1]["dtype"] == numpy.dtype(numpy.uint16).str
    received = numpy.frombuffer(blobs[1], descs[1]["dtype"])
    numpy.testing.assert_array_equal(received, spectrum)


def test_the_event_time_counts_from_the_start_of_the_count(live_updates):
    handler = make_handler()
    handler.dataset.started = time.time() - 5

    put(handler, numpy.zeros((2, 2)))

    assert live_updates[0][0]["time"] == pytest.approx(5, abs=1)


def test_missing_arrays_are_skipped(live_updates):
    put(make_handler(), None)

    assert live_updates == []


def test_an_array_that_is_not_real_numbers_is_left_out_with_a_warning(
    live_updates, caplog
):
    """A live view must not abort the count, which an error in putResults would."""
    put(make_handler(), numpy.ones((600, 600), numpy.complex64), numpy.arange(3.0))

    ((params, _blobs, _labels),) = live_updates
    assert [d["shape"] for d in params["datadescs"]] == [(3,)]
    assert "complex64" in caplog.text


def test_a_missing_array_leaves_the_others_with_their_own_description(live_updates):
    first = LiveArrayDesc("first", (3,), "<f8", ["energy"], title="First")
    second = LiveArrayDesc("second", (4,), "<f8", ["tof"], title="Second")

    put(make_handler(descs=[first, second]), None, numpy.arange(4.0))

    ((params, blobs, labels),) = live_updates
    assert len(params["datadescs"]) == 1
    frame = decode(params["datadescs"][0], blobs[0], labels)
    assert frame.dims == ("tof",)
    assert frame.title == "Second"


def test_arrays_get_default_dims_when_the_descriptions_do_not_match(live_updates):
    desc = LiveArrayDesc("only", (3,), "<f8", ["tof"], title="Only one")

    put(make_handler(descs=[desc]), numpy.arange(3.0), numpy.zeros((2, 2)))

    ((params, blobs, labels),) = live_updates
    frames = [decode(params["datadescs"][i], blobs[i], labels) for i in range(2)]
    assert [frame.dims for frame in frames] == [("x",), ("y", "x")]
    assert [frame.title for frame in frames] == ["", ""]


def test_nothing_is_sent_without_results_of_the_detector(live_updates):
    make_handler().putResults("live", {"other": ([], [numpy.arange(3.0)])})

    assert live_updates == []


def test_block_sums_too_large_for_uint16_are_sent_as_uint32(live_updates):
    put(make_handler(descs=HITS), numpy.full((2048, 2048), 60000, numpy.uint16))

    desc = live_updates[0][0]["datadescs"][0]
    assert desc["dtype"] == numpy.dtype(numpy.uint32).str
    assert desc["frame"]["meta"] == {}


def test_the_channel_description_travels_with_the_array(live_updates):
    desc = LiveArrayDesc(
        "monitor",
        (5,),
        "<f8",
        ["tof"],
        unit="counts",
        title="Monitor histogram",
        coords={"tof": Coord(("tof",), numpy.arange(6.0) * 1000, "us")},
        errors=numpy.ones(5),
    )

    put(make_handler(descs=[desc]), numpy.arange(5.0))

    ((params, blobs, labels),) = live_updates
    frame = decode(params["datadescs"][0], blobs[0], labels)
    assert frame.dims == ("tof",)
    assert frame.title == "Monitor histogram"
    assert frame.coords["tof"].unit == "us"
    numpy.testing.assert_array_equal(frame.errors, numpy.ones(5))


def test_a_plain_description_gives_pixels(live_updates):
    put(make_handler(descs=[ArrayDesc("cam", (3, 4), "<u2")]), numpy.zeros((3, 4)))

    frame = decode(
        live_updates[0][0]["datadescs"][0], live_updates[0][1][0], live_updates[0][2]
    )
    assert frame.dims == ("y", "x")
    assert frame.title == "cam"
