"""Time series of a single quantity, such as the total of an output."""

import numpy as np


class Series:
    """The latest (time, value) points of a series, oldest first.

    Times are in epoch seconds. The points live in one array that grows by
    doubling up to twice *maxlen*. After that the newest points move to a new
    array whenever the array is full. This way adding points or reading all
    points does not copy the whole series each time.
    """

    def __init__(self, maxlen=100_000):
        self.maxlen = maxlen
        self.clear()

    def __len__(self):
        return self._end - self._start

    def add(self, times, values):
        """Append a point, or arrays of points in time order.

        A point at the time of the last one replaces it. Older points are
        repeats of earlier updates and are ignored.
        """
        points = np.asarray([times, values], dtype=float).reshape(2, -1)
        if self:
            last = self._points[0, self._end - 1]
            points = points[:, np.searchsorted(points[0], last) :]
            if points.size and points[0, 0] == last:
                self._end -= 1
        points = points[:, -self.maxlen :]
        if self._end + points.shape[1] > self._points.shape[1]:
            first = max(self._start, self._end + points.shape[1] - self.maxlen)
            points = np.hstack([self._points[:, first : self._end], points])
            size = max(2 * self._points.shape[1], points.shape[1])
            self._points = np.empty((2, min(size, 2 * self.maxlen)))
            self._start = self._end = 0
        self._points[:, self._end : self._end + points.shape[1]] = points
        self._end += points.shape[1]
        self._start = max(self._start, self._end - self.maxlen)

    def clear(self):
        self._points = np.empty((2, 64))
        self._start = self._end = 0

    @property
    def last_value(self):
        return self._points[1, self._end - 1] if self else np.nan

    def arrays(self):
        """Return the times and values as a (2, n) float64 view.

        The view is valid until the next `add`.
        """
        return self._points[:, self._start : self._end]
