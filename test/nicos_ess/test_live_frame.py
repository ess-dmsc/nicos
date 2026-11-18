"""Tests for the reduction, wire format and projection of live frames."""

from dataclasses import replace

import numpy as np
import pytest

from nicos.utils import byteBuffer
from nicos_ess.utilities.frame_reduction import (
    block_sum,
    narrow,
    reduce,
    reduction_factors,
    sum_dtype,
)
from nicos_ess.utilities.frame_views import (
    axis,
    fit_window,
    flat_views,
    flatten,
    project,
    view_label,
    view_of,
    views,
)
from nicos_ess.utilities.live_frame import (
    FORMAT_VERSION,
    Coord,
    Frame,
    LiveArrayDesc,
    decode,
    encode,
    frame_of,
    frames,
)

session_setup = None


def roundtrip(*frames, version=None):
    datadescs, data, labels = encode(frames)
    if version is not None:
        datadescs[0]["frame"]["version"] = version
    data = [bytes(byteBuffer(b)) for b in data]
    labels = [bytes(byteBuffer(b)) for b in labels]
    return [decode(d, b, labels) for d, b in zip(datadescs, data, strict=True)]


def spectrum_cube():
    """Return a histogram over wavelength, y and x as esslivedata sends one."""
    rng = np.random.default_rng(0)
    return Frame(
        rng.poisson(2.0, size=(10, 64, 48)).astype(np.float64),
        ("wavelength", "y", "x"),
        unit="counts",
        counts=True,
        title="Detector counts",
        coords={
            "wavelength": Coord(("wavelength",), np.linspace(1.0, 6.0, 11), "angstrom"),
            "x": Coord(("x",), np.linspace(-0.2, 0.2, 48), "m"),
        },
        errors=np.full((10, 64, 48), 1.5),
    )


@pytest.mark.parametrize("dtype", ["uint16", "int16", "int32", "float32"])
@pytest.mark.parametrize("factors", [(2, 2), (3, 4), (2, 3, 4)])
def test_block_sum_sums_blocks_and_the_partial_blocks_at_the_end(dtype, factors):
    rng = np.random.default_rng(1)
    shape = (37, 50) if len(factors) == 2 else (4, 7, 9)
    data = rng.integers(0, 60000, size=shape).astype(dtype)

    padding = [(0, -n % f) for n, f in zip(shape, factors, strict=True)]
    padded = np.pad(data.astype(np.float64), padding)
    split = [s for n, f in zip(padded.shape, factors, strict=True) for s in (n // f, f)]
    expected = padded.reshape(split).sum(axis=tuple(range(1, 2 * len(factors), 2)))
    np.testing.assert_allclose(block_sum(data, factors), expected, rtol=1e-6)


def test_block_sum_does_not_overflow():
    reduced = block_sum(np.full((8, 8), 65535, np.uint16), (4, 4))

    assert reduced.dtype == np.uint32 and (reduced == 16 * 65535).all()
    assert sum_dtype(np.uint16, 2**16 + 1) == np.uint64
    assert sum_dtype(np.float32, 10) == np.float64


@pytest.mark.parametrize("counts", [True, False])
@pytest.mark.parametrize("value", [np.int64(2**62), np.uint64(2**64 - 1)])
def test_wide_integers_are_combined_without_overflow(counts, value):
    image = np.full((600, 600), value)

    reduced = reduce(Frame(image, ("y", "x"), counts=counts), 512 * 512)

    # Pairs of rows are combined.
    expected = float(value) * (2 if counts else 1)
    np.testing.assert_allclose(reduced.data.astype(np.float64), expected, rtol=1e-6)


@pytest.mark.parametrize(
    "values, expected",
    [
        ([0, 255], "uint8"),
        ([0, 65536], "uint32"),
        ([-1, 300], "int16"),
        ([-1, 127], "int8"),
        ([-1, 128], "int16"),
    ],
)
def test_sums_are_sent_in_the_smallest_exact_type(values, expected):
    narrowed = narrow(np.array(values, dtype=np.int64))

    assert narrowed.dtype == np.dtype(expected) and narrowed.tolist() == values


@pytest.mark.parametrize(
    "sizes, pixels, factors",
    [
        ({"y": 300, "x": 400}, 512 * 512, {"y": 1, "x": 1}),
        ({"tof": 50000}, 512 * 512, {"tof": 1}),
        ({"y": 2048, "x": 1024}, 512 * 256, {"y": 4, "x": 4}),
        ({"tof": 100, "y": 512, "x": 512}, 512 * 512, {"tof": 2, "y": 8, "x": 8}),
        # For an odd size the reduced image still fills the screen.
        ({"y": 2049, "x": 2049}, 512 * 512, {"y": 4, "x": 4}),
    ],
)
def test_reduction_factors(sizes, pixels, factors):
    assert reduction_factors(sizes, pixels) == factors


def camera_image():
    return np.random.default_rng(0).poisson(1000, (2048, 2048)).astype(np.uint16)


def test_counts_are_summed_and_their_total_kept():
    image = camera_image()

    hits = LiveArrayDesc("cam", (2048, 2048), "u2", "yx", counts=True)
    reduced = reduce(frame_of(image, hits), 512 * 512)

    assert reduced.data.shape == (512, 512) and reduced.data.dtype == np.uint16
    assert reduced.data.sum() == image.sum()
    assert reduced.binned == {"y": 4, "x": 4}
    assert reduced.errors is None


def test_counts_in_bins_that_do_not_fill_a_block_are_kept():
    image = np.ones((1021, 1031), np.uint16)
    coords = {
        "x": Coord(("x",), np.arange(1032.0)),
        "y": Coord(("y",), np.arange(1021.0)),
    }

    reduced = reduce(Frame(image, ("y", "x"), counts=True, coords=coords), 512 * 512)

    assert reduced.data.shape == (511, 258) and reduced.binned == {"y": 2, "x": 4}
    assert reduced.data.sum() == image.size
    assert reduced.coords["x"].values[-3:].tolist() == [1024.0, 1028.0, 1031.0]
    assert reduced.coords["y"].values[[0, -1]].tolist() == [0.5, 1020.0]


def test_an_image_that_is_not_counts_keeps_its_mean():
    image = camera_image()
    # The unit alone does not make the values counts, so they are averaged.
    frame = Frame(image, ("y", "x"), unit="counts")

    reduced = reduce(frame, 512 * 512)

    assert reduced.data.shape == (512, 512)
    assert reduced.data.mean() == pytest.approx(image.mean())


def test_on_chip_binning_multiplies_with_the_reduction():
    on_chip = LiveArrayDesc("cam", (2048, 2048), "u2", "yx", binned={"y": 2, "x": 2})

    reduced = reduce(frame_of(camera_image(), on_chip), 512 * 512)

    assert reduced.binned == {"y": 8, "x": 8}


def test_intensities_are_averaged_leaving_masked_bins_out():
    data = np.array([[4.0, np.nan, 2.0, 2.0, np.nan, np.nan]])

    reduced = reduce(Frame(data, ("y", "x"), unit="K"), 3)

    np.testing.assert_array_equal(reduced.data[0, :2], [4.0, 2.0])
    assert np.isnan(reduced.data[0, 2])


def test_the_error_of_a_mean_shrinks_with_the_number_of_bins():
    frame = Frame(np.ones((2, 2)), ("y", "x"), errors=np.full((2, 2), 2.0))

    # Four values with an error of 2 average to an error of sqrt(4 * 4) / 4.
    assert reduce(frame, 1).errors.tolist() == [[1.0]]


def test_errors_add_in_quadrature_and_coords_follow():
    cube = spectrum_cube()

    reduced = reduce(cube, 10 * 32 * 24)

    assert reduced.data.shape == (10, 32, 24)
    # Four bins with an error of 1.5 each add up to an error of 3.
    assert reduced.errors[0, 0, 0] == pytest.approx(3.0)
    assert reduced.errors.dtype == np.float32
    edges = reduced.coords["wavelength"].values
    np.testing.assert_array_equal(edges, cube.coords["wavelength"].values)
    x = cube.coords["x"].values
    assert reduced.coords["x"].values[0] == pytest.approx((x[0] + x[1]) / 2)


def test_bin_edges_keep_every_second_edge_when_bins_are_paired():
    edges = Coord(("wavelength",), np.arange(10.0), "angstrom")
    frame = Frame(
        np.arange(9.0), ("wavelength",), counts=True, coords={"wavelength": edges}
    )

    reduced = reduce(frame, 4)

    assert reduced.data.tolist() == [1.0, 5.0, 9.0, 13.0, 8.0]
    # The ninth bin does not fill a pair, so it stays alone with its upper edge.
    assert reduced.coords["wavelength"].values.tolist() == [0, 2, 4, 6, 8, 9]
    assert reduced.binned == {"wavelength": 2}


def test_times_stay_times():
    times = np.arange(8, dtype=np.int64) * 10**9
    frame = Frame(
        np.ones(8, np.int32),
        ("time",),
        coords={"time": Coord(("time",), times, "datetime64[ns]")},
    )

    reduced = reduce(frame, 4)

    assert reduced.coords["time"].values.dtype == np.int64
    assert reduced.coords["time"].values[0] == 5 * 10**8
    np.testing.assert_array_equal(axis(reduced, "time").values, [0.5, 2.5, 4.5, 6.5])
    assert axis(reduced, "time").is_time


def test_frames_survive_the_trip():
    cube = replace(
        spectrum_cube(), name="detector", binned={"y": 2}, meta={"time": 1.0}
    )
    spectrum = Frame(
        np.arange(5.0),
        ("tof",),
        coords={"tof": Coord(("tof",), np.arange(6.0) * 10, "us")},
    )
    empty = Frame(np.zeros((0, 5)), ("roi", "toa"), unit="counts", name="roi_spectra")

    received, second, nothing = roundtrip(cube, spectrum, empty)

    assert (received.dims, received.unit, received.title, received.counts) == (
        cube.dims,
        "counts",
        "Detector counts",
        True,
    )
    assert received.name == "detector"
    assert received.binned == {"y": 2}
    assert received.meta == {"time": 1.0}
    assert nothing.name == "roi_spectra"
    assert not second.counts and not nothing.counts
    np.testing.assert_array_equal(received.data, cube.data)
    np.testing.assert_array_equal(received.errors, cube.errors)
    for name, coord in cube.coords.items():
        assert received.coords[name].unit == coord.unit
        np.testing.assert_array_equal(received.coords[name].values, coord.values)
    np.testing.assert_array_equal(second.coords["tof"].values, np.arange(6.0) * 10)
    assert nothing.data.shape == (0, 5)


def test_plain_panels_get_labelled_axes():
    edges = Coord(("tof",), np.array([0, 2, 4, 7]), "ms")
    spectrum = Frame(np.ones(3), ("tof",), coords={"tof": edges})
    camera = reduce(frame_of(np.zeros((2048, 1024), np.uint16)), 512 * 256)
    pixels = Frame(np.zeros((2, 3)), ("y", "x"))

    datadescs, _data, buffers = encode([spectrum, camera, pixels])

    label = datadescs[0]["labels"]["x"]
    assert label["title"] == "tof (ms)"
    centres = np.frombuffer(bytes(byteBuffer(buffers[label["index"]])), label["dtype"])
    assert centres.tolist() == [1.0, 3.0, 5.5]
    # The x labels of a binned camera still count sensor pixels.
    assert datadescs[1]["labels"]["x"] == dict(
        define="range", start=1.5, step=4, length=256, title="x"
    )
    assert datadescs[2]["labels"] == {
        "x": dict(define="classic", title="x"),
        "y": dict(define="classic", title="y"),
    }


def test_frames_with_more_than_three_dims_get_numbered_dims():
    frame = frame_of(np.zeros((1, 2, 3, 4)))

    assert frame.sizes == {"dim_0": 1, "dim_1": 2, "dim_2": 3, "dim_3": 4}


def encoded_image():
    """Return the event of an image with an x coordinate and errors."""
    frame = Frame(
        np.ones((2, 3)),
        ("y", "x"),
        coords={"x": Coord(("x",), np.arange(4.0), "mm")},
        errors=np.ones((2, 3)),
        name="image",
    )
    datadescs, data, labels = encode([frame])
    return datadescs[0], [bytes(byteBuffer(b)) for b in [*data, *labels]]


@pytest.mark.parametrize(
    "key, value",
    [
        ("dims", ["x"]),
        ("dims", ["x", "x"]),
        ("coords", {"x": dict(index=1, dtype="<f8", shape=[4], dims=["y"], unit="")}),
        (
            "coords",
            {"x": dict(index=1, dtype="<f8", shape=[4], dims=["x"], unit="datetime64")},
        ),
        ("coords", []),
        ("errors", dict(index=1, dtype="<f8", shape=[4])),
        ("meta", [1]),
        ("meta", [("time", 1.0)]),
        ("binned", None),
        ("name", 5),
        ("counts", "false"),
        ("labels", None),
    ],
)
def test_an_event_that_holds_no_valid_frame_raises_value_error(key, value):
    datadesc, blobs = encoded_image()
    if key == "labels":
        datadesc.pop("frame")
        datadesc[key] = value
    else:
        datadesc["frame"][key] = value

    with pytest.raises(ValueError):
        list(frames(dict(det="cam", datadescs=[datadesc]), blobs))


@pytest.mark.parametrize("dtype", ["complex64", "datetime64[s]", "object"])
def test_frames_hold_real_numbers_only(dtype):
    with pytest.raises(ValueError):
        Frame(np.zeros(3, dtype), ("x",))


def test_plain_nicos_live_data_becomes_frames():
    data = np.arange(6, dtype="<u4").reshape(2, 3)
    desc = dict(
        dtype="<u4",
        shape=(2, 3),
        labels=dict(
            x=dict(define="range", start=10, step=2),
            y=dict(define="array", index=0, dtype="<f8"),
        ),
    )

    frame = decode(desc, data.tobytes(), [np.array([-1.0, 1.0]).tobytes()])

    assert frame.dims == ("y", "x")
    np.testing.assert_array_equal(frame.data, data)
    np.testing.assert_array_equal(frame.coords["x"].values, [10, 12, 14])
    np.testing.assert_array_equal(frame.coords["y"].values, [-1.0, 1.0])


def test_an_array_label_without_dtype_is_read_as_int32():
    """The generic NICOS live panel reads such labels as '<i4' too."""
    desc = dict(dtype="<f8", shape=(3,), labels=dict(x=dict(define="array", index=0)))
    data = np.zeros(3).tobytes()

    frame = decode(desc, data, [np.array([5, 6, 7], dtype="<i4").tobytes()])

    assert frame.coords["x"].values.dtype == np.dtype("<i4")
    assert frame.coords["x"].values.tolist() == [5, 6, 7]


def test_frames_are_named_after_channel_or_detector():
    plain = dict(dtype="<f8", shape=(2,))
    blob = np.arange(2.0).tobytes()
    datadescs, data, _labels = encode([Frame(np.ones(2), ("x",), name="orca")])

    one = frames(dict(det="cam", datadescs=[plain]), [blob])
    two = frames(dict(det="cam", datadescs=[plain] * 2), [blob] * 2)
    named = frames(dict(det="cam", datadescs=datadescs), [bytes(byteBuffer(data[0]))])

    assert [name for name, _frame in one] == ["cam"]
    assert [name for name, _frame in two] == ["cam[0]", "cam[1]"]
    assert [name for name, _frame in named] == ["orca"]


def test_a_newer_format_is_read_as_plain_live_data():
    (frame,) = roundtrip(spectrum_cube(), version=FORMAT_VERSION + 1)

    assert frame.dims == ("z", "y", "x") and frame.unit == ""


def test_dims_not_shown_are_summed_over_their_window():
    cube = spectrum_cube()

    image = project(cube, ("y", "x"))
    np.testing.assert_allclose(image.data, cube.data.sum(axis=0))
    np.testing.assert_allclose(image.errors, np.sqrt(10) * 1.5)
    assert "wavelength" not in image.coords

    line = project(cube, ("wavelength",), {"y": (3, 4), "x": (7, 8)})
    np.testing.assert_array_equal(line.data, cube.data[:, 3, 7])
    assert axis(line, "wavelength").is_edges
    assert project(cube, ("x", "wavelength")).data.shape == (48, 10)
    window = project(cube, ("y", "x"), {"wavelength": (2, 5), "x": (0, 1)})
    np.testing.assert_allclose(window.data, cube.data[2:5].sum(axis=0))
    np.testing.assert_allclose(window.errors, np.sqrt(3) * 1.5)
    full = project(cube, ("y", "x"), {"wavelength": (0, 10)})
    np.testing.assert_array_equal(full.data, image.data)


def test_values_that_are_not_counts_are_averaged_over_the_window():
    data = np.array([[1.0, 2.0], [3.0, np.nan], [8.0, 6.0]])
    frame = Frame(data, ("tof", "x"), unit="K")
    np.testing.assert_allclose(project(frame, ("x",), {"tof": (0, 2)}).data, [2, 2])
    np.testing.assert_allclose(project(frame, ("x",), {"tof": (2, 3)}).data, [8, 6])


def test_counts_are_summed_over_the_window_leaving_masked_bins_out():
    counts = Frame(
        np.arange(6, dtype=np.uint16).reshape(3, 2), ("tof", "x"), counts=True
    )
    summed = project(counts, ("x",), {"tof": (1, 3)}).data
    assert summed.tolist() == [6, 8] and summed.dtype == np.uint32
    data = np.array([[1.0, 2.0], [3.0, np.nan], [8.0, 6.0]])
    gap = Frame(data, ("tof", "x"), counts=True)
    np.testing.assert_allclose(project(gap, ("x",), {"tof": (1, 3)}).data, [11, 6])
    # A window of only masked bins has no sum.
    assert np.isnan(project(gap, ("x",), {"tof": (1, 2)}).data[1])


def test_a_window_keeps_its_width_inside_a_shorter_dim():
    assert fit_window((3000, 3100), 2000) == (1900, 2000)
    assert fit_window((3, 4), 2) == (1, 2)
    assert fit_window((10, 3100), 2000) is None
    assert fit_window((0, 5), 5) is None and fit_window(None, 5) is None
    assert fit_window((-2, 3), 10) == (0, 5)
    assert fit_window((3, 3), 10) == (3, 4)


def test_views_image_first_then_pairs_then_curves():
    cube = spectrum_cube()

    assert views(cube) == [
        ("y", "x"),
        ("wavelength", "y"),
        ("wavelength", "x"),
        ("wavelength",),
        ("y",),
        ("x",),
    ]
    choice = flat_views(cube)[0]
    assert view_label(choice) == "wavelength·y × x"
    assert view_of(cube, choice).data.shape == (10 * 64, 48)
    blades = Frame(
        np.ones((2, 3, 4)),
        ("a", "b", "c"),
        coords={"a": Coord(("a",), np.arange(2.0)), "c": Coord(("c",), np.arange(4.0))},
        binned={"b": 2, "c": 2},
    )
    flat = flatten(blades, ("a", "b"), "a/b")
    assert flat.dims == ("a/b", "c") and flat.data.shape == (6, 4)
    assert list(flat.coords) == ["c"] and flat.binned == {"c": 2}


@pytest.mark.parametrize("shape", [(7, 5, 0), (0, 5, 3)])
def test_frames_with_an_empty_dim_give_empty_views(shape):
    frame = Frame(np.zeros(shape, np.int32), ("a", "b", "c"), counts=True)
    a, b, c = shape

    flat = [view_of(frame, choice).data.shape for choice in flat_views(frame)]

    assert flat == [(a * b, c), (a, b * c)]
    assert reduce(frame, 4).data.shape == shape


def test_an_x_y_image_is_drawn_with_x_across():
    """esslivedata stores the Timepix image as (x, y), but y still goes up."""
    data = np.arange(6).reshape(3, 2)
    frame = Frame(data, ("x", "y"), unit="counts")

    assert views(frame)[0] == ("y", "x")
    np.testing.assert_array_equal(view_of(frame, ("y", "x")).data, data.T)


def test_axis_without_coord_counts_source_pixels():
    frame = Frame(np.ones((2, 3)), ("y", "x"), binned={"x": 4})

    np.testing.assert_array_equal(axis(frame, "x").values, [1.5, 5.5, 9.5])
    np.testing.assert_array_equal(axis(frame, "y").values, [0.0, 1.0])


@pytest.mark.parametrize("counts", [True, False], ids=["sum", "mean"])
@pytest.mark.parametrize("operation", ["reduce", "project"])
def test_a_masked_bin_contributes_no_uncertainty(counts, operation):
    frame = Frame(
        np.array([[10.0, np.nan]]),
        ("y", "x"),
        counts=counts,
        errors=np.array([[2.0, 100.0]]),
    )

    combined = reduce(frame, 1) if operation == "reduce" else project(frame, ("y",))
    np.testing.assert_array_equal(combined.data.ravel(), [10.0])
    np.testing.assert_allclose(combined.errors.ravel(), [2.0])
