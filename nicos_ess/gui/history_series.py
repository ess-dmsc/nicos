"""Time series of cache readings for the history viewer.

A cache value stays valid until it changes, so a series stores only the
readings that were received, and plots draw them as steps up to now.
"""

import bisect
import numbers
import time

import numpy as np

from nicos.utils import KEYEXPR_NS

# All strings beyond the limit of a series share the number of this state.
OTHER = "other"


class HistorySeries:
    """Readings of one cache key, optionally transformed by an expression.

    A reading less than *interval* after the second newest point replaces
    the newest point, so there are at most two points per interval, and the
    latest value and the first reading after a pause are kept. With a
    *window*, older readings are dropped except the one that is valid at the
    start of the window. Above ``maxsize`` points the repeated values are
    dropped first. If more than half of the points are changes of value, every
    second point of the older half is dropped as well, so changes get lost
    there too.
    """

    maxsize = 100_000
    maxstrings = 20  # Only this many strings outside the mapping get their own number.

    def __init__(self, descr, expr, interval, window=None, unit=None, mapping=None):
        self.descr, self.expr, self.window, self.unit = descr, expr, window, unit
        self.interval = max(float(interval or 0), 0.0)
        self.string_mapping = dict(mapping or {})
        self._string_limit = len(self.string_mapping) + self.maxstrings
        # The readings lie between these indices, so the window drops old ones in place.
        self._x, self._y = np.empty(64), np.empty(64)
        self._start = self._end = 0

    @property
    def label(self):
        """Return the name followed by the numbers that stand for strings.

        Strings that spell their own number are left out, for example a speed
        of 14 shown as "14".
        """
        pairs = sorted(self.string_mapping.items(), key=lambda item: item[1])
        pairs = [f"{i:g}={name}" for name, i in pairs if str(name) != f"{i:g}"]
        return f"{self.descr} ({', '.join(pairs)})" if pairs else self.descr

    @property
    def title(self):
        """Return the label, or the name with the unit if nothing is mapped."""
        if self.unit and self.label == self.descr:
            return f"{self.descr} ({self.unit})"
        return self.label

    @property
    def n(self):
        return self._end - self._start

    @property
    def x(self):
        return self._x[self._start : self._end]

    @property
    def y(self):
        return self._y[self._start : self._end]

    def load(self, history):
        """Replace the readings with *history*, which holds ``(time, raw value)``
        pairs in time order."""
        self._start = self._end = 0
        for vtime, value in history:
            self.add(vtime, value)

    def add(self, vtime, value):
        """Store a reading.

        Return False if the reading is not a number or is older than the
        newest one. A reading stamped later than now counts as read now, so a
        device with a wrong clock cannot block the readings that follow.
        """
        value, vtime = self.convert(value), min(vtime, time.time())
        if value is None or (self.n and vtime < self._x[self._end - 1]):
            return False
        if self.n >= 2 and vtime - self._x[self._end - 2] < self.interval:
            self._end -= 1
        elif self.n >= self.maxsize:
            self._thin()
        if self._end == len(self._x):
            self._keep(slice(None))
        self._x[self._end], self._y[self._end] = vtime, value
        self._end += 1
        if self.window:
            first = int(np.searchsorted(self.x, vtime - self.window, side="right"))
            self._start += max(first - 1, 0)
        return True

    def convert(self, value):
        try:
            if value is not None and self.expr:
                value = eval(self.expr, KEYEXPR_NS, {"x": value})
            if isinstance(value, str):
                mapping = self.string_mapping
                if value not in mapping:
                    if len(mapping) >= self._string_limit:
                        value = OTHER
                    mapping.setdefault(value, max(mapping.values(), default=-1) + 1)
                value = mapping[value]
            return float(value) if isinstance(value, numbers.Real) else None
        except Exception:
            return None

    def _thin(self):
        keep = np.ones(self.n, dtype=bool)
        keep[1:] = self.y[1:] != self.y[:-1]
        keep[-1] = True
        if keep.sum() > self.maxsize // 2:
            index = np.arange(self.n)
            keep &= (index >= self.n // 2) | (index % 2 == 0)
        self._keep(keep)

    def _keep(self, mask):
        x, y = self.x[mask], self.y[mask]
        self._start, self._end = 0, len(x)
        self._x, self._y = (np.resize(a, max(64, 2 * len(a))) for a in (x, y))


def column_names(fmtstr, ncolumns):
    """Return the column names of a multi-value from its format string.

    For a format like ``"%d, roi0 = %d"`` each name is the text before
    " = ". An unnamed first column holds the value of the device itself and
    gets the name "". Return None if the format does not give all *ncolumns*
    unique names.
    """
    pieces = fmtstr.split(", ") if isinstance(fmtstr, str) else []
    if ncolumns < 2 or len(pieces) != ncolumns:
        return None
    names = []
    for index, piece in enumerate(pieces):
        name, named, _ = piece.partition(" = ")
        if not named and index:
            return None
        names.append(name.strip() if named else "")
    return names if len(set(names)) == len(names) else None


class ColumnNames:
    """Format strings of a device over time, used to name the value columns.

    A device can change what its columns contain, for example when an
    esslivedata channel adds a column per ROI. Each value is therefore named
    with the format that was valid when the value was read.
    """

    def __init__(self, history=()):
        self._times, self._formats = [], []
        for vtime, fmtstr in history:
            self.add(vtime, fmtstr)

    def add(self, vtime, fmtstr):
        index = bisect.bisect_right(self._times, vtime)
        self._times.insert(index, vtime)
        self._formats.insert(index, fmtstr)

    def named(self, vtime, value):
        """Return a dict from column name to value for *value* read at *vtime*.

        Return None if the columns have no names.
        """
        if not self._formats or not isinstance(value, (list, tuple)):
            return None
        index = max(bisect.bisect_right(self._times, vtime) - 1, 0)
        names = column_names(self._formats[index], len(value))
        return None if names is None else dict(zip(names, value, strict=True))
