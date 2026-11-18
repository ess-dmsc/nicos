"""The daemon and the GUI share these self-describing live data frames.

A `Frame` holds one detector output, which is the content of an esslivedata
da00 message or a plain camera image. A channel describes its array with a
`LiveArrayDesc`. The daemon reduces the array with `frame_reduction.reduce`
and sends it with `encode`. Clients read it with `decode` and use
`frame_views` to pick what to plot.

Each datadesc has the standard NICOS keys ``dtype``, ``shape`` and ``labels``,
so panels that do not know about frames still show the data with labelled
axes. A ``frame`` key holds the rest::

    frame = {
        "version": 1,                        # FORMAT_VERSION
        "name": "detector_image",            # name of the channel
        "dims": ["wavelength", "y", "x"],    # in C order with one dim per shape entry
        "unit": "counts",
        "counts": True,                      # see Frame.counts
        "title": "Detector counts",
        "coords": {"wavelength": {"dims": ["wavelength"], "unit": "angstrom",
                                  "index": 2, "dtype": "<f8", "shape": [101]}},
        "errors": {"index": 3, "dtype": "<f8", "shape": [101, 64, 48]} or None,
        "binned": {"x": 4, "y": 4},          # number of source bins per shown bin
        "meta": {"time": 1763300000.0},      # source details, see Frame.meta
    }

``index`` points into the label buffers. The buffers of the standard
``labels`` come first, so that older panels find them where they expect. A
client treats a newer ``version`` than it knows as plain NICOS live data.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace

import numpy

from nicos.core.params import ArrayDesc

DEFAULT_DIMS = ("z", "y", "x")

# Increase when older clients would misread the format.
FORMAT_VERSION = 1

_PLAIN = dict(name=str, unit=str, counts=bool, title=str, binned=dict, meta=dict)

# A time coordinate has the unit datetime64[<unit>] with one of these units,
# which give the seconds per value.
SECONDS = dict(h=3600, m=60, s=1, ms=1e-3, us=1e-6, ns=1e-9)


def default_dims(ndim):
    """Return dim names like ``("y", "x")``, or ``dim_0`` and so on beyond 3 dims."""
    if ndim > 3:
        return tuple(f"dim_{i}" for i in range(ndim))
    return DEFAULT_DIMS[3 - ndim :]


@dataclass(frozen=True)
class Coord:
    """A coordinate has n bin centres or n + 1 bin edges along *dims*.

    A unit like ``datetime64[ns]`` marks integer times since the epoch, which
    is how da00 sends times. `SECONDS` lists the units that can go in brackets.
    """

    dims: tuple[str, ...]
    values: numpy.ndarray
    unit: str = ""

    def __post_init__(self):
        if self.is_time and self.seconds_per_value is None:
            raise ValueError(f"unknown time unit {self.unit}")

    @property
    def is_time(self):
        return self.unit.startswith("datetime64")

    @property
    def seconds_per_value(self):
        """Return the seconds per value of a time coordinate, else None."""
        return SECONDS.get(self.unit[11:-1]) if self.is_time else None

    def fits(self, sizes):
        """Return True if the coordinate has n or n + 1 values along each of its
        dims, where *sizes* gives n."""
        shape = numpy.shape(self.values)
        return len(shape) == len(self.dims) and all(
            d in sizes and n - sizes[d] in (0, 1)
            for d, n in zip(self.dims, shape, strict=True)
        )


@dataclass(frozen=True)
class Frame:
    data: numpy.ndarray
    dims: tuple[str, ...]
    unit: str = ""  # The unit is free text that nothing parses.
    # True if the values are counts, which are summed when bins are combined.
    # Other values are averaged. The source sets this because the unit does
    # not tell.
    counts: bool = False
    title: str = ""
    coords: dict[str, Coord] = field(default_factory=dict)
    errors: numpy.ndarray | None = None  # The errors are standard deviations.
    binned: dict[str, int] = field(default_factory=dict)
    name: str = ""  # This is the name of the channel that read the array.
    # Details from the source, such as the esslivedata workflow that ROIs are
    # sent back to.
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        """Raise ValueError if the parts of the frame do not fit together."""
        for key, kind in _PLAIN.items():
            if not isinstance(getattr(self, key), kind):
                raise ValueError(f"{key} of a frame must be a {kind.__name__}")
        if len(set(self.dims)) < len(self.dims):
            raise ValueError(f"repeated dims in {self.dims}")
        # The frame of a LiveArrayDesc has no data.
        if self.data is not None:
            self._check_data()

    def _check_data(self):
        shape = self.data.shape
        if self.data.dtype.kind not in "biuf":
            raise ValueError(f"data of type {self.data.dtype} is not real numbers")
        if len(shape) != len(self.dims):
            raise ValueError(f"dims {self.dims} for data of shape {shape}")
        if self.errors is not None and numpy.shape(self.errors) != shape:
            raise ValueError(f"errors of shape {numpy.shape(self.errors)} for {shape}")
        for name, coord in self.coords.items():
            if not coord.fits(self.sizes):
                raise ValueError(f"coordinate {name} does not fit {self.sizes}")

    @property
    def sizes(self):
        return dict(zip(self.dims, self.data.shape, strict=True))


def float_array(values):
    """Return *values* as a float array, or an empty array if numpy cannot
    convert them."""
    try:
        return numpy.asarray(values, dtype=float)
    except (TypeError, ValueError, OverflowError):
        return numpy.array([])


def curve_frame(dim, unit, x, y, x_unit="", **fields):
    """Return a 1-D frame of the values *y* at *x*, which are bin centres or edges."""
    coords = {dim: Coord((dim,), numpy.asarray(x), x_unit or "")}
    return Frame(numpy.asarray(y), (dim,), unit or "", coords=coords, **fields)


class LiveArrayDesc(ArrayDesc):
    """An `ArrayDesc` that carries the `Frame` of the last array read, without data.

    A channel sets a new description for every array.
    """

    def __init__(self, name, shape, dtype, dims, *, title="", **fields):
        ArrayDesc.__init__(self, name, shape, dtype, list(dims))
        self.frame = Frame(None, tuple(dims), title=title or name, name=name, **fields)

    @classmethod
    def of(cls, frame, name):
        """Return the description of *frame*, which the channel *name* read."""
        desc = cls(name, frame.data.shape, frame.data.dtype, frame.dims)
        desc.frame = replace(frame, data=None, name=name, title=frame.title or name)
        return desc

    def copy(self):
        return copy.copy(self)


def frame_of(array, desc=None):
    """Return a `Frame` for an array read from a channel with *desc*."""
    array = numpy.asarray(array)
    if isinstance(desc, LiveArrayDesc) and len(desc.dimnames) == array.ndim:
        return replace(desc.frame, data=array)
    name = desc.name if desc is not None else ""
    return Frame(array, default_dims(array.ndim), title=name, name=name)


def dim_coord(frame, dim):
    """Return a 1-D coordinate of centres or edges along *dim*, or None."""
    for coord in [frame.coords.get(dim), *frame.coords.values()]:
        if coord and coord.dims == (dim,):
            return coord
    return None


def _standard_label(frame, dim, buffers):
    """Return a plain NICOS label of *dim* for panels that ignore frames."""
    coord = dim_coord(frame, dim)
    factor = frame.binned.get(dim, 1)
    if coord is None and factor > 1:
        n = frame.sizes[dim]
        start = (factor - 1) / 2
        return dict(define="range", start=start, step=factor, length=n, title=dim)
    if coord is None or coord.is_time:
        return dict(define="classic", title=dim)
    values = numpy.asarray(coord.values, dtype=numpy.float64)
    if len(values) > frame.sizes[dim]:  # Plain labels have one value per bin.
        values = (values[:-1] + values[1:]) / 2
    buffers.append(values)
    title = f"{dim} ({coord.unit})" if coord.unit else dim
    return dict(define="array", index=len(buffers) - 1, dtype="<f8", title=title)


def _raw(array):
    """Return *array* as flat bytes, which `byteBuffer` accepts even if empty."""
    return numpy.ascontiguousarray(array).reshape(-1).view(numpy.uint8)


def encode(frames):
    """Return datadescs, data buffers and label buffers for `updateLiveData`."""
    standard, extra = [], []
    labels = [
        {
            key: _standard_label(f, dim, standard)
            for key, dim in zip("xy", f.dims[::-1], strict=False)
        }
        for f in frames
    ]

    def put(array):
        extra.append(array := numpy.asarray(array))
        index = len(standard) + len(extra) - 1
        return dict(index=index, dtype=array.dtype.str, shape=list(array.shape))

    datadescs = []
    for frame, plain in zip(frames, labels, strict=True):
        info = {k: getattr(frame, k) for k in _PLAIN}
        info["coords"] = {
            name: dict(dims=list(c.dims), unit=c.unit, **put(c.values))
            for name, c in frame.coords.items()
        }
        info["errors"] = None if frame.errors is None else put(frame.errors)
        info.update(version=FORMAT_VERSION, dims=list(frame.dims))
        dtype, shape = frame.data.dtype.str, frame.data.shape
        datadescs.append(
            dict(dtype=dtype, shape=shape, labels=plain, plotcount=1, frame=info)
        )
    data = [_raw(f.data) for f in frames]
    return datadescs, data, [_raw(b) for b in standard + extra]


def decode(datadesc, databuffer, labelbuffers):
    """Return the `Frame` of *datadesc*. This also works for plain NICOS live data."""
    data = numpy.frombuffer(databuffer, dtype=datadesc["dtype"])
    data = data.reshape(tuple(datadesc["shape"]))

    def buffer(index, dtype, shape=-1, **_):
        return numpy.frombuffer(labelbuffers[index], dtype=dtype).reshape(shape)

    info = datadesc.get("frame")
    if info is not None and info["version"] <= FORMAT_VERSION:
        coords = {
            name: Coord(tuple(c["dims"]), buffer(**c), c["unit"])
            for name, c in info["coords"].items()
        }
        errors = info["errors"] and buffer(**info["errors"])
        plain = {k: info[k] for k in _PLAIN}
        return Frame(data, tuple(info["dims"]), coords=coords, errors=errors, **plain)
    dims = default_dims(data.ndim)
    coords, labels = {}, datadesc.get("labels", {})
    for key, dim, n in zip("xy", dims[::-1], data.shape[::-1], strict=False):
        label = labels.get(key, {})
        if label.get("define") == "range":
            start, step = label.get("start", 0), label.get("step", 1)
            coords[dim] = Coord((dim,), start + step * numpy.arange(n, dtype=float))
        elif label.get("define") == "array":
            values = buffer(label.get("index", 0), label.get("dtype", "<i4"))
            coord = Coord((dim,), values)
            # Plain live data can have labels of another length, which are left out.
            if coord.fits({dim: n}):
                coords[dim] = coord
    return Frame(data, dims, coords=coords)


def frames(parameters, blobs):
    """Yield the channel or detector name and the `Frame` of each array in an event.

    An event that does not hold valid frames raises ValueError.
    """
    try:
        datadescs, det = parameters["datadescs"], parameters["det"]
        for i, (desc, blob) in enumerate(zip(datadescs, blobs, strict=False)):
            frame = decode(desc, blob, blobs[len(datadescs) :])
            yield frame.name or (det if len(datadescs) == 1 else f"{det}[{i}]"), frame
    except (KeyError, IndexError, TypeError, AttributeError) as err:
        raise ValueError(f"unreadable live data: {err!r}") from err
