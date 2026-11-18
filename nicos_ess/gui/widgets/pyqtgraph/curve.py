"""A plot curve with error bars, drawn as lines or as steps."""

import numpy as np
import pyqtgraph as pg

from nicos_ess.gui.widgets.pyqtgraph.theme import LINE_WIDTH


class _Line(pg.PlotDataItem):
    """A line whose autorange can include 0.

    Peaks of counts only look right against a zero baseline.
    """

    # The autorange includes 0 on this axis, which is 0 for x and 1 for y.
    floor_axis = None

    def dataBounds(self, ax, frac=1.0, orthoRange=None):
        low, high = super().dataBounds(ax, frac, orthoRange)
        if ax == self.floor_axis and low is not None:
            low = min(low, 0.0)
            # Without any counts 0 stays at the bottom.
            high = high if high > 0 else 1.0
        return low, high


class Curve:
    """A curve on a `PlotItem` or `ViewBox`.

    With one more x than y, x holds bin edges and the curve is drawn as
    steps.
    """

    def __init__(self, plot, color):
        self.color = pg.mkColor(color)
        self.line = _Line(connect="finite")
        # Downsampling keeps the min and max of each pixel.
        self.line.opts["autoDownsampleFactor"] = 1.0
        self.errors = pg.ErrorBarItem(beam=0)
        # This marks the points that have no neighbours.
        self.lone = pg.ScatterPlotItem(size=6)
        self.floor = self.symbols = False
        self.lines = True
        self.log = False
        self._data = None
        self._add_to(plot)
        self.line.visibleChanged.connect(self._show_errors)
        self._style()

    def set_data(self, x, y, errors=None, *, hold=False):
        """Set the data of the curve.

        With *hold* each value stays until the next x instead of joining the
        points. This suits readings that are valid until the next one.
        """
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        if errors is not None:
            errors = np.abs(np.asarray(errors, dtype=float))
        self._data = (x, y, errors, hold)
        self._draw()

    def set_style(self, *, lines=True, symbols=False):
        # Without lines the symbols are shown, so the curve never disappears.
        self.lines, self.symbols = lines, symbols or not lines
        self._style()

    def set_floor(self, on):
        """Include 0 in the value range, as counts need, unless the scale is log."""
        if on != self.floor:
            self.floor = on
            self._draw()

    def set_log(self, log):
        """Draw the values on a log scale if *log* is set."""
        if log != self.log:
            self.log = log
            # This also works for a curve in a separate view box.
            self.line.setLogMode(False, log)
            self._draw()

    def move_to(self, plot):
        """Move the curve to another plot or to a view box with its own axis."""
        self.remove()
        self._add_to(plot)

    def _add_to(self, plot):
        self.plot = plot
        plot.addItem(self.line)
        for item in (self.errors, self.lone):
            plot.addItem(item, ignoreBounds=True)

    def remove(self):
        for item in (self.line, self.errors, self.lone):
            self.plot.removeItem(item)

    def _style(self):
        self.line.setPen(pg.mkPen(self.color, width=LINE_WIDTH) if self.lines else None)
        self.line.setSymbol("o" if self.symbols else None)
        self.line.setSymbolSize(6)
        self.line.setSymbolPen(pg.mkPen(self.color))
        self.line.setSymbolBrush(pg.mkBrush(self.color))
        self.errors.setOpts(pen=pg.mkPen(self.color, width=1))
        self.lone.setPen(None)
        self.lone.setBrush(pg.mkBrush(self.color))
        self._draw()

    def _draw(self):
        if self._data is None:
            return
        x, y, _errors, hold = self._data
        self.line.floor_axis = 1 if self.floor and not self.log else None
        x, y, steps, many = self._line_points(x, y)
        self.line.setData(
            x, y, stepMode="center" if steps else ("right" if hold else None)
        )
        # This comes after setData because it redraws the line.
        self.line.setDownsampling(auto=many, method="peak")
        self._draw_errors()
        self._draw_lone(x, y, steps)

    def _line_points(self, x, y):
        """Return the points of the line, whether they are steps and whether
        there are so many that the line is downsampled."""
        steps = len(x) == len(y) + 1
        if self.log and not (y > 0).any():
            # Otherwise pyqtgraph warns on every paint.
            return x[:0], y[:0], False, False
        # Many points are drawn as the min and max of each pixel. Symbols are
        # not downsampled because they would vanish in a fraction of a wide view.
        many = self.lines and not self.symbols and len(y) > 4096
        if steps and many:
            # Draw the steps as a line through the same corners, so that the
            # downsampling thins them the same way.
            x, y, steps = np.repeat(x, 2)[1:-1], np.repeat(y, 2), False
        return x, y, steps, many

    def _draw_lone(self, x, y, steps):
        # Lines do not show a finite point between two gaps, so mark it.
        shown = self.lines and self.line.opts["symbol"] is None and not steps
        if shown and len(x) == len(y):
            with np.errstate(divide="ignore", invalid="ignore"):
                y = np.log10(y) if self.log else y
            ok = np.isfinite(x) & np.isfinite(y)
            near = np.pad(ok, 1)
            lone = ok & ~near[:-2] & ~near[2:]
            x, y = x[lone], y[lone]
        else:
            x = y = []
        self.lone.setData(x=x, y=y)
        self._show_errors()

    def _draw_errors(self):
        x, y, dy, _hold = self._data
        if dy is not None:
            if len(x) == len(y) + 1:
                x = (x[:-1] + x[1:]) / 2
            centre, top, bottom = y, dy, dy
            if self.log:
                with np.errstate(divide="ignore", invalid="ignore"):
                    centre = np.where(y > 0, np.log10(y), np.nan)
                    top = np.log10(y + dy) - centre
                    bottom = np.where(y - dy > 0, centre - np.log10(y - dy), np.nan)
            keep = np.isfinite(x) & np.isfinite(centre)
            top, bottom = (np.where(np.isfinite(a), a, 0)[keep] for a in (top, bottom))
            x, centre = x[keep], centre[keep]
            self.errors.setData(x=x, y=centre, top=top, bottom=bottom)

    def _show_errors(self):
        shown = self._data is not None and self._data[2] is not None
        self.errors.setVisible(shown and self.line.isVisible())
        self.lone.setVisible(len(self.lone.data) > 0 and self.line.isVisible())
