"""Combine bins of a `Frame` to downsample it for display or to project it.

Counts are summed and other values are averaged. Masked bins are NaN and are
left out, and errors are added in quadrature.
"""

from __future__ import annotations

import math
from dataclasses import replace

import numpy

from nicos_ess.utilities.live_frame import Coord, dim_coord


def sum_dtype(dtype, count):
    """Return a dtype that holds the sum of *count* values of *dtype*.

    Integer sums that could need more than 64 bits are floats.
    """
    dtype = numpy.dtype(dtype)
    bits = 8 * dtype.itemsize + math.ceil(math.log2(max(count, 1)))
    if dtype.kind not in "iu" or bits > 64:
        return numpy.dtype(numpy.float64)
    return numpy.dtype(f"{dtype.kind}{4 if bits <= 32 else 8}")


def block_sum(array, factors):
    """Sum blocks of ``factors[axis]`` bins along each axis with `sum_dtype`.

    The last block along an axis holds the bins that are left over. Adding
    strided slices is faster than ``reshape().sum()``. For 2048 x 2048 uint16
    in 4 x 4 blocks it takes 4 ms instead of 5 to 20 ms.
    """
    dtype = sum_dtype(array.dtype, math.prod(factors))
    for axis, f in enumerate(factors):
        if f > 1:
            parts = [
                array[(slice(None),) * axis + (slice(o, None, f),)] for o in range(f)
            ]
            array = parts[0].astype(dtype)
            for part in parts[1:]:
                array[(slice(None),) * axis + (slice(part.shape[axis]),)] += part
    return array


def combine(frame, total):
    """Return data and errors of *frame* summed over blocks by *total*.

    Values that are not counts are then averaged over the non-NaN bins.
    """
    data, errors = frame.data, frame.errors
    floating = data.dtype.kind == "f"
    # Counts without NaN need no count of valid bins, which saves two copies.
    if floating and frame.counts and not numpy.isnan(data).any():
        floating = False
    if errors is not None:
        errors = _summed_errors(errors, data, floating, total)
    if not floating and frame.counts:
        return total(data), errors
    data, count = _valid_sums(data, floating, total)
    with numpy.errstate(invalid="ignore", divide="ignore"):
        if frame.counts:
            return numpy.where(count > 0, data, numpy.nan), errors
        return data / count, None if errors is None else errors / count


def _summed_errors(errors, data, floating, total):
    """Return the errors of the sums of *total*.

    The errors of NaN values in *data* count as zero. Unless *floating* is
    set, no value is NaN.
    """
    squares = numpy.square(errors)
    if floating:
        squares = numpy.where(numpy.isnan(data), 0, squares)
    return numpy.sqrt(total(numpy.nan_to_num(squares)))


def _valid_sums(data, floating, total):
    """Return the sums of *total* over the values of *data* that are not NaN
    and the number of those values.

    Unless *floating* is set, no value is NaN.
    """
    if not floating:
        return total(data), total(numpy.ones(data.shape, bool))
    valid = ~numpy.isnan(data)
    return total(numpy.where(valid, data, 0)), total(valid)


def reduction_factors(sizes, maxpoints):
    """Return the number of bins to combine per dim to fit *maxpoints*.

    Each step halves the longest side, and among equal sides the one that was
    reduced least. This keeps image bins square and leaves a spectrum alone
    unless it is very large.
    """
    factors = dict.fromkeys(sizes, 1)
    while sizes and math.prod(sizes[d] // factors[d] for d in sizes) > maxpoints:
        dim = max(sizes, key=lambda d: (sizes[d] // factors[d], -factors[d]))
        if sizes[dim] // factors[dim] <= 1:
            break
        factors[dim] *= 2
    return factors


def narrow(values):
    """Convert *values* to the smallest dtype that holds them exactly.

    This saves bytes on the wire. Floats become float32, which is exact for
    counts up to 2**24 per bin.
    """
    if values.dtype.kind == "f":
        return values.astype(numpy.float32)
    if values.size == 0:
        return values
    lo, hi = int(values.min()), int(values.max())
    return values.astype(numpy.min_scalar_type(min(lo, -hi - 1) if lo < 0 else hi))


def _reduce_coord(coord, sizes, factors):
    """Keep every f-th bin edge and the last one, and average bin centres over
    blocks of f."""
    values = numpy.asarray(coord.values)
    per_axis = []
    for axis, dim in enumerate(coord.dims):
        f, n = factors.get(dim, 1), sizes[dim]
        if values.shape[axis] == n + 1:
            values = numpy.take(values, [*range(0, n, f), n], axis=axis)
            f = 1
        per_axis.append(f)
    if any(f > 1 for f in per_axis):
        ones = numpy.ones(values.shape)
        values = block_sum(values.astype(numpy.float64), per_axis)
        values = values / block_sum(ones, per_axis)
        if coord.is_time:
            values = values.astype(numpy.int64)
    return replace(coord, values=values)


def _pixel_edges(frame, factors):
    """Return pixel edge coordinates for the dims that end in a partial bin.

    Without them a pixel axis would draw the partial bin as wide as a full one.
    """
    coords = {}
    for dim, f in factors.items():
        n = frame.sizes[dim]
        if n % f and dim_coord(frame, dim) is None:
            pixels = numpy.append(numpy.arange(0, n, f), n) * frame.binned.get(dim, 1)
            coords[dim] = Coord((dim,), pixels - 0.5)
    return coords


def reduce(frame, maxpoints):
    """Return the frame with bins combined to at most *maxpoints* full bins.

    The bins left over at the end of a dim form one more partial bin, so no
    counts are lost. The partial bins do not count towards *maxpoints*, so an
    image of 2049 x 2049 still gets square bins of 4 x 4 and fills the screen.
    A pixel axis with a partial bin gets bin edges from `_pixel_edges`, so the
    last bin ends at the sensor edge. The factors are recorded in ``binned``.
    The data always goes through `narrow`.
    """
    factors = reduction_factors(frame.sizes, maxpoints)
    data, errors = frame.data, frame.errors
    coords, binned = frame.coords, frame.binned
    if any(f > 1 for f in factors.values()):
        per_axis = [factors[d] for d in frame.dims]
        data, errors = combine(frame, lambda a: block_sum(a, per_axis))
        coords = {k: _reduce_coord(c, frame.sizes, factors) for k, c in coords.items()}
        coords.update(_pixel_edges(frame, factors))
        binned = {d: binned.get(d, 1) * f for d, f in factors.items()}
        binned = {d: f for d, f in binned.items() if f > 1}
    if errors is not None:
        errors = numpy.asarray(errors, dtype=numpy.float32)
    data = narrow(numpy.asarray(data))
    return replace(frame, data=data, errors=errors, coords=coords, binned=binned)
