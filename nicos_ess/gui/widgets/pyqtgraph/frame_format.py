"""This module formats the bin edges, titles and readouts of plotted frames.

It does not use Qt.
"""

import time

import numpy as np

from nicos_ess.utilities.frame_views import axis

SI = ((1e12, "T"), (1e9, "G"), (1e6, "M"), (1e3, "k"))


def edges_of(ax):
    """Return the bin edges of an axis.

    An axis of bin centres gets edges half way between the centres.
    """
    values = np.asarray(ax.values, dtype=np.float64)
    if ax.is_edges:
        return values
    if len(values) < 2:
        return np.concatenate([values - 0.5, values + 0.5])
    mids = (values[:-1] + values[1:]) / 2
    return np.concatenate(
        [[2 * values[0] - mids[0]], mids, [2 * values[-1] - mids[-1]]]
    )


def pointer_edges(view):
    """Return the edges that the pointer uses to find values in a 1-D view.

    These are the bins, or the spans from each point to the next if
    ``meta["hold"]`` is set.
    """
    ax = axis(view, view.dims[0])
    if view.meta.get("hold") and not ax.is_edges:
        return np.append(ax.values, ax.values[-1:]).astype(np.float64)
    return edges_of(ax)


def keeps_proportions(x, y):
    """Return whether an image is drawn with square units.

    Axes with the same unit, such as metres on a detector face, keep their
    proportions, but Q against energy does not. Pixel axes also keep them
    unless the image is a long strip such as the 15 x 900 image of BIFROST,
    where each row would become a thin line.
    """
    if x.is_time or y.is_time or x.unit != y.unit:
        return False
    xe, ye = edges_of(x), edges_of(y)
    width, height = abs(xe[-1] - xe[0]), abs(ye[-1] - ye[0])
    return bool(x.unit) or max(width, height) <= 4 * min(width, height)


def shown_dims(choice):
    """Return the frame dims that a view choice shows.

    Merged dims are tuples in the choice.
    """
    return {
        d for part in choice for d in (part if isinstance(part, tuple) else (part,))
    }


def clock(t):
    """Return the local time of day of *t*, or "–" if the system has no date for it."""
    try:
        return time.strftime("%H:%M:%S", time.localtime(t))
    except (OverflowError, OSError, ValueError):
        return "–"


def is_pixels(ax):
    """Return True if *ax* has no unit and bin edges at half integers, like pixels."""
    return not ax.unit and bool(np.allclose(edges_of(ax) % 1, 0.5))


def format_position(ax, index, stop=None):
    """Return the position of bin *index*, or of the bins up to *stop*, as text.

    This is a range like "1.2–1.4 Å", a time of day, or a pixel like "66".
    A bin of 4 pixels gives "64–67".
    """
    edges = edges_of(ax)
    lo, hi = edges[index], edges[index + 1 if stop is None else stop]
    if ax.is_time:
        return clock((lo + hi) / 2) if stop is None else f"{clock(lo)}–{clock(hi)}"
    if is_pixels(ax):
        lo, hi = sorted((lo, hi))
        lo, hi = round(lo + 0.5), round(hi - 0.5)
        return f"{lo}" if lo == hi else f"{lo}–{hi}"
    # "-480 to -384" reads better than "-480–-384".
    dash = " to " if min(lo, hi) < 0 else "–"
    if stop is None or max(abs(lo), abs(hi)) >= 1e6:
        return f"{readable(lo)}{dash}{readable(hi)} {ax.unit}".rstrip()
    # Both ends get the decimals that tell the narrowest bin from its neighbours.
    width = np.abs(np.diff(edges[index : stop + 1])).min()
    digits = max(0, -int(np.floor(np.log10(width)))) if width > 0 else 0
    return f"{lo:,.{digits}f}{dash}{hi:,.{digits}f} {ax.unit}".rstrip()


def facts(frame, total):
    """Return the parts of the title of a frame, the most important first.

    The parts are the *total* from `total_of`, the source and shown shape
    and the start time. A frame without data has no parts because
    the plot already says "No data". The range sliders under the plot show
    how the other dims are combined.
    """
    if not frame.data.size:
        return []
    kind = "Σ" if frame.counts else "mean"
    parts = [f"{kind} {readable(total)} {frame.unit}".rstrip()]
    # The mean of a history means nothing.
    parts[0] *= not frame.meta.get("hold")
    shown = "×".join(map(str, frame.data.shape))
    source = "×".join(str(n * frame.binned.get(d, 1)) for d, n in frame.sizes.items())
    shape = source if source == shown else f"{source}, shown {shown}"
    # A curve over time has points instead of bins.
    if frame.data.ndim == 1:
        shape += " points" if axis(frame, frame.dims[0]).is_time else " bins"
    parts.append(shape)
    if frame.meta.get("start_time"):
        parts.append("since " + clock(frame.meta["start_time"]))
    return parts


def age_text(age, period=0.0):
    """Return the age of the data as text.

    Return "" if the age is below 5 s or below two *period*s between frames.
    Data this late is normal, and an age that comes and goes would blink.
    """
    if age is None or age < max(5, 2 * period):
        return ""
    if age < 120:
        return f"{age:.0f} s old"
    return f"{age / 60:.0f} min old" if age < 7200 else f"{age / 3600:.0f} h old"


def total_of(frame):
    """Return the sum of a frame for counts, otherwise its mean."""
    data = np.asarray(frame.data)
    # Integers have no NaN, so a plain sum is much faster.
    if data.dtype.kind in "iu":
        total = data.sum(dtype=np.int64)
        return float(total if frame.counts else total / max(data.size, 1))
    if not np.isfinite(data).any():
        return np.nan
    return float(np.nansum(data) if frame.counts else np.nanmean(data))


def same_unit(a, b):
    return (a or None) == (b or None)


def close(a, b):
    return len(a) == len(b) and np.allclose(a, b, rtol=1e-6, atol=1e-9)


def axis_label(ax):
    """Return the label and unit of an axis.

    A time axis gets no unit because pyqtgraph would add an SI prefix to it.
    """
    return ax.dim, (None if ax.is_time or not ax.unit else ax.unit)


def bin_index(edges, value):
    """Return the bin of *value* in ascending or descending *edges*, or None."""
    flipped = bool((edges[:1] > edges[-1:]).any())
    edges = edges[::-1] if flipped else edges
    index = int(np.searchsorted(edges, value, side="right")) - 1
    if not 0 <= index < len(edges) - 1:
        return None
    return len(edges) - 2 - index if flipped else index


def readable(value, digits=4):
    """Return a number formatted the same way in every plot.

    Whole numbers below a million are shown in full like 949,800. Larger
    numbers get *digits* digits and a prefix like 1.158G. Other numbers get
    *digits* digits like 0.1234. Axis ticks use the shorter
    `theme.compact_number`.
    """
    value = float(value)
    if not np.isfinite(value):
        return "–"
    for scale, suffix in SI:
        if abs(value) >= scale >= 1e6:
            return f"{value / scale:.{digits}g}{suffix}"
    if value.is_integer() or abs(value) >= 1e3:
        return f"{value:,.0f}"
    return f"{value:.{digits}g}"


def with_unit(value, unit, error=None):
    """Return *value* with *unit* and an optional *error*, such as "1 count"."""
    text = readable(value)
    if error is not None:
        text += f" ± {readable(float(f'{error:.2g}'))}"
    return f"{text} {'count' if unit == 'counts' and value == 1 else unit}".rstrip()


def value_text(view, index):
    errors = None if view.errors is None else view.errors[index]
    return with_unit(view.data[index], view.unit, errors)


def pointer_at(view, x, y=None):
    """Return the position of (x, y) in a projected frame and the bin index there.

    Return None if the point is outside the frame.
    """
    if view.data.ndim == 1:
        ax = axis(view, view.dims[0])
        i = bin_index(pointer_edges(view), x)
        if i is None:
            return None
        where = clock(x) if view.meta.get("hold") else format_position(ax, i)
        return f"{ax.dim} {where}", (i,)
    y_ax, x_ax = (axis(view, dim) for dim in view.dims)
    i, j = bin_index(edges_of(y_ax), y), bin_index(edges_of(x_ax), x)
    if i is None or j is None:
        return None
    where = ", ".join(
        f"{ax.dim} {format_position(ax, k)}" for ax, k in ((x_ax, j), (y_ax, i))
    )
    return where, (i, j)
