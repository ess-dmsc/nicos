"""These functions pick the 1-D and 2-D views of a `Frame` for plotting."""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, replace

import numpy

from nicos_ess.utilities.frame_reduction import combine, sum_dtype
from nicos_ess.utilities.live_frame import dim_coord


@dataclass(frozen=True)
class Axis:
    """An axis holds the bin centres or bin edges of one dim and their unit."""

    dim: str
    values: numpy.ndarray
    unit: str = ""
    is_edges: bool = False
    is_time: bool = False


def axis(frame, dim):
    """Return the `Axis` of *dim*.

    Without a coordinate the values are source pixel indices. Times are
    converted to seconds since the epoch.
    """
    n = frame.sizes[dim]
    coord = dim_coord(frame, dim)
    if coord is None:
        f = frame.binned.get(dim, 1)
        return Axis(dim, (f - 1) / 2 + f * numpy.arange(n, dtype=numpy.float64))
    values = numpy.asarray(coord.values, dtype=numpy.float64)
    unit = coord.unit
    if coord.is_time:
        values, unit = values * coord.seconds_per_value, "s"
    return Axis(dim, values, unit, len(values) == n + 1, coord.is_time)


def project(frame, shown, windows=None):
    """Return the frame reduced to the dims *shown*, in that order.

    Every other dim is combined over its window in *windows*, or over all of
    it. A window is a (start, stop) range of bins. Counts are summed and other
    values are averaged, see `combine`. Coordinates along a removed dim are
    dropped.
    """
    data, errors = _combine_hidden(frame, shown, windows)
    dims = [d for d in frame.dims if d in shown]
    order = [dims.index(d) for d in shown]
    return replace(
        frame,
        data=numpy.transpose(data, order),
        errors=None if errors is None else numpy.transpose(errors, order),
        dims=tuple(shown),
        coords={k: c for k, c in frame.coords.items() if set(c.dims) <= set(shown)},
        binned={d: f for d, f in frame.binned.items() if d in shown},
    )


def _combine_hidden(frame, shown, windows):
    """Return the data and errors of *frame* combined over the windows of
    the dims that are not *shown*.
    """
    windows = {d: w for d, w in (windows or {}).items() if d not in shown}
    index = tuple(slice(*windows.get(d, (None, None))) for d in frame.dims)
    errors = None if frame.errors is None else frame.errors[index]
    cut = replace(frame, data=frame.data[index], errors=errors, coords={})
    hidden = tuple(i for i, d in enumerate(frame.dims) if d not in shown)
    if not hidden:
        return cut.data, errors
    n = math.prod(cut.data.shape[i] for i in hidden)
    return combine(cut, lambda a: a.sum(axis=hidden, dtype=sum_dtype(a.dtype, n)))


def fit_window(window, size):
    """Return *window* moved and cut to fit a dim of *size* bins.

    The window keeps its width where it can. A window over the whole dim is
    None, which also stands for the whole dim.
    """
    if window is None:
        return None
    start, stop = window
    width = max(1, min(stop - start, size))
    start = max(0, min(start, size - width))
    return None if width >= size else (start, start + width)


def flatten(frame, dims, to):
    """Merge the adjacent *dims* into one dim *to*.

    The outer dim comes first in *dims*.
    """
    first = frame.dims.index(dims[0])
    last = first + len(dims)
    shape = frame.data.shape
    shape = (*shape[:first], math.prod(shape[first:last]), *shape[last:])
    return replace(
        frame,
        data=frame.data.reshape(shape),
        errors=None if frame.errors is None else frame.errors.reshape(shape),
        dims=(*frame.dims[:first], to, *frame.dims[last:]),
        coords={k: c for k, c in frame.coords.items() if not set(c.dims) & set(dims)},
        binned={d: f for d, f in frame.binned.items() if d not in dims},
    )


def views(frame):
    """Return the views of *frame* as tuples of dims.

    The default image comes first, then the other pairs of dims, then single
    dims as curves.
    """
    dims = frame.dims
    if len(dims) < 2:
        return [dims]
    pairs = list(itertools.combinations(dims, 2))
    default = pairs.pop(pairs.index(dims[-2:]))
    if default == ("x", "y"):
        # esslivedata sends Timepix images with the dims x, y. Swap them so that
        # x runs across like in a camera image.
        default = ("y", "x")
    return [default, *pairs, *((dim,) for dim in dims)]


def flat_views(frame):
    """Return image views of a 3-D frame with two adjacent dims merged.

    This is for the blade x wire x strip data of ESTIA, which gives views such
    as ``((blade, wire), strip)``.
    """
    d = frame.dims
    return [((d[0], d[1]), d[2]), (d[0], (d[1], d[2]))] if len(d) == 3 else []


def _name(part):
    return "·".join(part) if isinstance(part, tuple) else part


def view_of(frame, choice, windows=None):
    """Return the frame for one view from `views` or `flat_views`.

    The view sums or averages the other dims over their *windows*, see
    `project`.
    """
    for part in choice:
        if isinstance(part, tuple):
            frame = flatten(frame, part, _name(part))
    return project(frame, tuple(map(_name, choice)), windows)


def view_label(choice):
    return " × ".join(map(_name, choice))
