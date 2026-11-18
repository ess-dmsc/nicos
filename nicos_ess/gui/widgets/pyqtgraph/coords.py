"""Image coordinate conversions."""

import numpy as np


def to_world(edges, pixel):
    """Convert pixel positions to coordinates along ascending or descending *edges*.

    Pixel i spans edges i and i + 1, so its centre is at pixel position i.
    The mapping is linear within each bin and extrapolated beyond the ends.
    """
    at = np.asarray(pixel, dtype=float) + 0.5
    i = np.clip(np.floor(at), 0, len(edges) - 2).astype(int)
    return edges[i] + (at - i) * (edges[i + 1] - edges[i])


def to_pixel(edges, value):
    """Convert coordinates to pixel positions as the inverse of `to_world`."""
    if edges[0] > edges[-1]:
        return len(edges) - 2 - to_pixel(edges[::-1], value)
    value = np.asarray(value, dtype=float)
    i = np.clip(np.searchsorted(edges, value) - 1, 0, len(edges) - 2)
    width = edges[i + 1] - edges[i]
    return i + (value - edges[i]) / np.where(width == 0, 1, width) - 0.5


class CoordinateGrid:
    """Mapping between pixel indices and data coordinates of a 2D image with
    the bin edges *x* and *y*."""

    def __init__(self, x, y):
        self._edges = dict(x=np.asarray(x, dtype=float), y=np.asarray(y, dtype=float))

    def same_as(self, other):
        """Return True if *other* maps pixels to the same coordinates."""
        return other is not None and all(
            np.array_equal(self._edges[a], other._edges[a]) for a in "xy"
        )

    def pixel_to_world(self, x, y):
        return tuple(
            float(to_world(self._edges[a], v))
            for a, v in zip("xy", (x, y), strict=True)
        )

    def world_to_pixel(self, x, y):
        return tuple(
            float(to_pixel(self._edges[a], v))
            for a, v in zip("xy", (x, y), strict=True)
        )
