"""Plots on a grid of 12 columns that has no holes.

A layout is an ordered list of spans ``(name, w, h)``, the width in columns
and the height in rows of each plot. `pack` places the plots like a CSS grid
with ``grid-auto-flow: dense`` and then closes the gaps that are left, so
every row reaches the right edge. The user changes the list and never the
places, and after each change the layout keeps the spans that `pack` gave,
so what the user sees is what is saved.
"""

from __future__ import annotations

import fnmatch
import itertools
import math
from dataclasses import dataclass

COLUMNS = 12
MIN_WIDTH = 2
# A plot only joins the last row when it gets at least this many columns.
JOIN_WIDTH = 3


@dataclass
class Cell:
    name: str
    x: int
    y: int
    w: int
    h: int

    def rect(self):
        return (self.x, self.y, self.w, self.h)

    def span(self):
        return (self.name, self.w, self.h)

    def rows(self):
        return range(self.y, self.y + self.h)


def bottom(cells):
    return max((c.y + c.h for c in cells), default=0)


def by_row(cells):
    return sorted(cells, key=lambda c: (c.y, c.x))


def spans_of(cells):
    """Return the spans of placed *cells* in the order of their places."""
    return [c.span() for c in by_row(cells)]


def find(cells, name):
    return next((c for c in cells if c.name == name), None)


def row_of(cells, cell):
    """Return the plots of *cells* that start in the row of *cell* and are as high."""
    return [c for c in cells if (c.y, c.h) == (cell.y, cell.h)]


def covered(cells):
    """Return the plot that covers each cell (x, y)."""
    return {(x, y): c for c in cells for y in c.rows() for x in range(c.x, c.x + c.w)}


def free(at, x0, x1, rows):
    return all((x, y) not in at for x in range(x0, x1) for y in rows)


def holes(cells):
    """Return the empty cells above the bottom of *cells*."""
    at = covered(cells)
    return [
        (x, y) for y in range(bottom(cells)) for x in range(COLUMNS) if (x, y) not in at
    ]


def pack(spans, keep=None):
    """Return the cells of *spans* placed densely and without holes.

    Each plot in turn goes to the first place from the top left where it
    fits. A gap that is left is closed by the plots left of it, which widen,
    or else by those right of it, or else by those above it, which grow down.
    The plot *keep*, which the user resizes, only grows if no other plot can.
    A plot is at most COLUMNS rows high.
    """
    spans = [
        (n, min(max(w, MIN_WIDTH), COLUMNS), min(max(h, 1), COLUMNS))
        for n, w, h in spans
    ]
    while True:
        for fixed in [keep, None] if keep else [None]:
            cells = _place(spans)
            row = _close_gaps(cells, fixed)
            if row is None:
                return cells
        # The tallest plot in the row of the gap that stays gets a row shorter.
        # If every plot in that row is one row high, the tallest plot anywhere
        # gets a row shorter.
        near = {c.name for c in cells if row in c.rows()}
        tallest = max(
            spans, key=lambda s: (s[2] > 1 and s[0] in near, s[2], s[0] != keep)
        )
        if tallest[2] == 1:
            return cells
        spans = [(n, w, h - (n == tallest[0])) for n, w, h in spans]


def _place(spans):
    at, cells = {}, []
    for name, w, h in spans:
        places = ((x, y) for y in itertools.count() for x in range(COLUMNS - w + 1))
        x, y = next((x, y) for x, y in places if free(at, x, x + w, range(y, y + h)))
        cells.append(Cell(name, x, y, w, h))
        at.update(covered(cells[-1:]))
    return cells


def _close_gaps(cells, keep):
    """Close the gaps of *cells* in place and return the row of one that stays."""
    while found := holes(cells):
        x, y = found[0]
        at = covered(cells)
        end = x
        while end < COLUMNS and (end, y) not in at:
            end += 1
        if not (
            _widen(at, x, end, y, keep, -1)
            or _widen(at, x, end, y, keep, 1)
            or _grow_down(at, x, end, y, keep)
        ):
            return y
    return None


def _widen(at, x, end, y, keep, side):
    """Let the plots left (*side* -1) or right (1) of the gap widen into it.

    These are the plots next to each other in row *y* that start in that row
    and have the same height as the plot next to the gap.
    """
    near = at.get((x - 1, y) if side < 0 else (end, y))
    if near is None or near.y != y or not free(at, x, end, near.rows()):
        return False
    chain = [near]
    while True:
        last = chain[-1]
        neighbour = at.get((last.x - 1, y) if side < 0 else (last.x + last.w, y))
        if neighbour is None or (neighbour.y, neighbour.h) != (y, near.h):
            break
        chain.append(neighbour)
    growing = [c for c in chain if c.name != keep]
    if not growing:
        return False
    for _ in range(end - x):
        # The narrowest plot gets the next column, and of equal ones the one
        # nearest to the gap.
        min(growing, key=lambda c: (c.w, chain.index(c))).w += 1
    start = min(c.x for c in chain) if side < 0 else x
    for cell in sorted(chain, key=lambda c: c.x):
        cell.x = start
        start += cell.w
    return True


def _grow_down(at, x, end, y, keep):
    """Let the plots right above the gap grow down into it."""
    if y == 0:
        return False
    above = {at[i, y - 1].name: at[i, y - 1] for i in range(x, end)}
    inside = all(
        x <= c.x and c.x + c.w <= end and c.h < COLUMNS for c in above.values()
    )
    if not inside or keep in above:
        return False
    for cell in above.values():
        cell.h += 1
    return True


def swap(cells, a, b):
    """Return the spans of *cells* with the plots *a* and *b* swapped."""
    spans = spans_of(cells)
    i, j = [k for k, s in enumerate(spans) if s[0] in (a, b)]
    spans[i], spans[j] = spans[j], spans[i]
    return spans


def insert(cells, name, target, after):
    """Return the spans of *cells* with *name* put next to *target*, or None.

    *name* goes before *target*, or after it if *after* is true. A plot from
    another row takes the height of the plots in the row of *target*, and they
    share their width with it. If the row has no room for one more plot, this
    returns None.
    """
    moving, target_cell = find(cells, name), find(cells, target)
    rest = [c for c in by_row(cells) if c.name != name]
    if moving is not None and (moving.y, moving.h) == (target_cell.y, target_cell.h):
        new, widths = moving.span(), {}
    else:
        row = row_of(rest, target_cell)
        total = sum(c.w for c in row)
        if total < MIN_WIDTH * (len(row) + 1):
            return None
        width = max(MIN_WIDTH, round(total / (len(row) + 1)))
        new = (name, width, target_cell.h)
        widths = _leaving(rest, moving) | _shared(row, total - width)
    spans = [(c.name, widths.get(c.name, c.w), c.h) for c in rest]
    at = next(i for i, s in enumerate(spans) if s[0] == target) + bool(after)
    spans.insert(at, new)
    return spans


def _shared(row, total):
    """Return the widths of the plots in *row* when they share *total* columns."""
    return {
        c.name: w for c, w in zip(row, share(total, [c.w for c in row]), strict=True)
    }


def _leaving(rest, moving):
    """Return the widths of the plots in the row that *moving* leaves.

    They share its width, so no other plot moves up into its place.
    """
    row = row_of(rest, moving) if moving else []
    return _shared(row, sum(c.w for c in row) + moving.w) if row else {}


def share(total, weights):
    """Split *total* columns in proportion to *weights*, each at least MIN_WIDTH."""
    weight = sum(weights) or 1
    exact = [total * w / weight for w in weights]
    parts = [max(MIN_WIDTH, math.floor(e)) for e in exact]
    order = sorted(range(len(parts)), key=lambda i: parts[i] - exact[i])
    # Rounding down loses less than one column per part, so each part needs
    # at most one more column.
    for i in order:
        if sum(parts) >= total:
            break
        parts[i] += 1
    while sum(parts) > total and max(parts) > MIN_WIDTH:
        parts[parts.index(max(parts))] -= 1
    return parts


def new_row(cells, name, h=1):
    """Return the spans of *cells* with *name* in a row of its own at the bottom."""
    rest = [c for c in by_row(cells) if c.name != name]
    widths = _leaving(rest, find(cells, name))
    spans = [(c.name, widths.get(c.name, c.w), c.h) for c in rest]
    return spans + [(name, COLUMNS, h)]


def resize(cells, name, w, h):
    """Return the cells with the plot *name* resized to *w* x *h*.

    If the height stays, a wider plot takes the columns from the plots next
    to it in its row, nearest first and down to their minimum width, and a
    narrower one gives them to its neighbour. Whatever does not fit flows on
    to the next rows.
    """
    cell = find(cells, name)
    row = [c for c in row_of(cells, cell) if c is not cell]
    widths = {c.name: c.w for c in row}
    near = sorted(row, key=lambda c: (c.x < cell.x, abs(c.x - cell.x)))
    change = w - cell.w
    if h != cell.h:
        givers = []
    elif change > 0:
        givers = near
    else:
        givers = near[:1]
    for other in givers:
        give = min(change, widths[other.name] - MIN_WIDTH)
        widths[other.name] -= give
        change -= give
    spans = [
        (n, w, h) if n == name else (n, widths.get(n, cw), ch)
        for n, cw, ch in spans_of(cells)
    ]
    return pack(spans, keep=name)


def add(cells, name):
    """Return the spans of *cells* with the new plot *name* at the end.

    It joins the last row if that row is one row high and every plot there
    keeps JOIN_WIDTH columns. Otherwise it starts a new row.
    """
    if not cells:
        return [(name, COLUMNS, 1)]
    last = by_row(cells)[-1]
    row = row_of(cells, last)
    if last.h == 1 and sum(c.w for c in row) >= JOIN_WIDTH * (len(row) + 1):
        return insert(cells, name, last.name, True)
    return new_row(cells, name)


def arrange(names, spans):
    """Return the packed layout of *names* from their saved *spans*.

    *spans* may hold plots that are gone for now. A name without a span goes
    after the plots of its own output if there are any (an ROI plot
    "ngem.roi0" after "ngem"), and otherwise at the end.
    """
    known = [s for s in spans if s[0] in names]
    cells = pack(known)
    for name in sorted(set(names) - {s[0] for s in known}):
        output = name.split(".")[0]
        family = [c.name for c in by_row(cells) if c.name.split(".")[0] == output]
        spans = insert(cells, name, family[-1], True) if family else None
        cells = pack(spans or add(cells, name))
    return cells


def from_preset(names, patterns):
    """Return the spans of *names* from the cells (x, y, w, h) in *patterns*.

    *patterns* maps names or fnmatch wildcards to cells. A name gets the cell
    of its own name, or else of the first pattern that matches it. The spans
    follow the order of the cells.
    """
    rects = {}
    for name in names:
        found = [p for p in patterns if fnmatch.fnmatchcase(name, p)]
        if name in patterns or found:
            rects[name] = patterns[name if name in patterns else found[0]]
    order = sorted(rects, key=lambda n: (rects[n][1], rects[n][0], n))
    return [(n, rects[n][2], rects[n][3]) for n in order]


def automatic(names, width, height, aspect):
    """Return the spans of full rows of equal plots that are close to *aspect*.

    A row holds at most COLUMNS / MIN_WIDTH plots. Rows differ by at most one
    plot, and a plot only has a row to itself when every row has one plot.
    """
    count = len(names)
    if not count:
        return []
    width, height = max(width, 1), max(height, 1)

    def row_counts(rows):
        return [count // rows + (i < count % rows) for i in range(rows)]

    def cost(rows):
        counts = row_counts(rows)
        if counts[0] > COLUMNS // MIN_WIDTH or counts[-1] == 1 < counts[0]:
            return math.inf
        shape = [abs(math.log(width / k / (height / rows) / aspect)) for k in counts]
        return sum(k * s for k, s in zip(counts, shape, strict=True)) / count

    spans, names = [], list(names)
    for k in row_counts(min(range(1, count + 1), key=cost)):
        cols = [COLUMNS // k + (i >= k - COLUMNS % k) for i in range(k)]
        spans += [(names.pop(0), w, 1) for w in cols]
    return spans
