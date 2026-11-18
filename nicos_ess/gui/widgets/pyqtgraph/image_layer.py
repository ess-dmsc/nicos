"""An image on a plot has a colour bar whose two handles set the levels.

Evenly spaced bins are drawn as an image and other bins as a mesh. A log scale
and the option to hide values at or below the low level set these values to
NaN, and both items leave NaN out.
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.widgets.ColorMapMenu import buildMenuEntryAction

from nicos.guisupport.qt import (
    QActionGroup,
    QLabel,
    QObject,
    QSignalBlocker,
    Qt,
    pyqtSignal,
)
from nicos_ess.gui.widgets.pyqtgraph.plot_parts import (
    NumberForm,
    add_widget,
    check_action,
    radio_entries,
)
from nicos_ess.gui.widgets.pyqtgraph.theme import (
    ACCENT,
    COLORMAP_GROUPS,
    COLORMAPS,
    SLATE,
    CompactAxisItem,
    fix_axis_room,
)

# The automatic levels come from a sample of this many pixels and leave out a
# few hot or dead pixels.
LEVEL_SAMPLE = 250_000
LEVEL_PERCENTILES = (0.5, 99.5)
# One wheel step widens or narrows the levels by this factor.
WHEEL_STEP = 1.15
BAR_WIDTH, COMPACT_BAR_WIDTH = 22, 14  # px
# The bar reserves room for tick labels as wide as this one.
WIDE_TICK = "888k"
# The bar extends beyond each level by this fraction of the level span.
MARGIN = 0.25
COLORBAR_TIP = (
    "The handles mark the colour levels. Drag a handle or the band between them.\n"
    "The wheel widens or narrows the levels.\n"
    "Levels set here stay until you choose Scale to each image in the Colours"
    " menu.\n"
    "A right-click opens the plot menu, which has the Colours menu."
)
# These modes decide when new images set the colour levels.
LEVEL_MODES = {
    "always": "Scale to each image",
    "once": "Scale to the first image",
    "manual": "Keep the levels as set",
}


def log_values(values):
    """Return log10 of *values*, with NaN for non-positive values."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(values > 0, np.log10(values), np.nan)


def auto_levels(values):
    """Return colour levels for *values* that leave out outliers.

    If nearly all values are equal, as early in a count, the high level is the
    maximum. Flat data gets the levels [v, v + 1].
    """
    # A strided sample of a big image gives the same levels much faster.
    sample = values.ravel()[:: max(1, values.size // LEVEL_SAMPLE)]
    finite = sample[np.isfinite(sample)]
    if not finite.size:
        return 0.0, 1.0
    low, high = np.percentile(finite, LEVEL_PERCENTILES)
    return float(low), float(high if high > low else max(finite.max(), low + 1))


def colormap(name, reverse=False):
    # pyqtgraph has its own copies of viridis and a few other maps. These do
    # not need matplotlib, whose import takes about half a second.
    source = None if name in pg.colormap.listMaps() else "matplotlib"
    cmap = pg.colormap.get(name, source=source, skipCache=True)
    if reverse:
        cmap.reverse()
    return cmap


def _even(edges):
    # Allow 1/1000 of a bin so that float32 and epoch time edges count as even.
    even = np.linspace(edges[0], edges[-1], len(edges))
    return np.allclose(edges, even, rtol=0, atol=abs(even[1] - even[0]) / 1000)


class _BarBox(pg.ViewBox):
    """This view box holds the colour bar.

    The wheel sets the levels. Double and right clicks go to the plot, so the
    plot menu and "only this plot" work on the bar too.
    """

    bar = None

    def wheelEvent(self, ev, axis=None):
        self.bar.wheel(ev)

    def mouseClickEvent(self, ev):
        if ev.double() or ev.button() == Qt.MouseButton.RightButton:
            self.bar.layer.plot.vb.mouseClickEvent(ev)

    def mouseDragEvent(self, ev, axis=None):
        ev.ignore()


class ColorBar(pg.PlotItem):
    """A colour bar that spans the levels plus a margin to drag them into.

    The bar draws the real mapping from values to colours, so clipping and
    transparency show on it. On a log scale the ticks are values like 1, 10
    and 100. The bar goes below 0 only if the data or the levels do.
    """

    def __init__(self, layer):
        box = _BarBox(enableMenu=False)
        super().__init__(viewBox=box, axisItems={"right": CompactAxisItem("right")})
        box.bar, self.layer = self, layer
        box.setMouseEnabled(False, False)
        self.hideButtons()
        self.hideAxis("left")
        self.hideAxis("bottom")
        self.showAxis("right")
        self.axis = self.getAxis("right")
        self.setToolTip(COLORBAR_TIP)
        self.bar = pg.ImageItem(axisOrder="row-major")
        self.addItem(self.bar)
        self.handles = pg.LinearRegionItem(
            orientation="horizontal",
            brush=pg.mkBrush(None),
            pen=pg.mkPen(SLATE, width=1.5),
            hoverPen=pg.mkPen(ACCENT, width=2),
            hoverBrush=pg.mkBrush(255, 255, 255, 50),
            swapMode="block",
        )
        for line in self.handles.lines:
            line.addMarker("<|>", position=0.12, size=7)
            line.addMarker("<|>", position=0.88, size=7)
        self.handles.sigRegionChanged.connect(self._dragged)
        self.handles.sigRegionChangeFinished.connect(self._released)
        self.addItem(self.handles)
        self.span = (0.0, 1.0)
        # The span stays fixed while a handle is dragged.
        self.held = False
        self.set_compact(False)

    def set_compact(self, compact):
        """Switch to a narrower bar without a label. The plot title shows the unit."""
        self.compact = compact
        self.layout.setColumnFixedWidth(1, COMPACT_BAR_WIDTH if compact else BAR_WIDTH)
        labelled = not compact and bool(self.axis.labelText)
        self.axis.showLabel(labelled)
        label = self.axis.label.boundingRect().height() * 0.8 if labelled else 0.0
        fix_axis_room(self.axis, WIDE_TICK, label)

    def set_label(self, text):
        self.axis.setLabel(text)
        self.set_compact(self.compact)

    def redraw(self):
        layer = self.layer
        low, high = layer.drawn_levels()
        bottom, top = self.span
        # While the levels move only a little the scale stays and the handles move.
        inside = bottom <= low and high <= top and high - low > (top - bottom) / 3
        if not self.held and not inside:
            margin = (high - low) * MARGIN
            floor = -np.inf if layer.log or min(low, layer.range[0]) < 0 else 0
            self.span = (max(low - margin, floor), high + margin)
        bottom, top = self.span
        values = np.linspace(bottom, top, 256)[:, None]
        if layer.transparent_low:
            values[values <= low] = np.nan
        self.bar.setImage(values, autoLevels=False, levels=(low, high))
        self.bar.setColorMap(layer.cmap)
        self.bar.setRect(0, bottom, 1, top - bottom)
        self.vb.setRange(xRange=(0, 1), yRange=(bottom, top), padding=0)
        # Block the signals because moving the handles here is no drag by the user.
        with QSignalBlocker(self.handles):
            self.handles.setBounds((bottom, top))
            self.handles.setRegion((low, high))

    def _dragged(self):
        self.held = True
        low, high = self.handles.getRegion()
        if high > low:
            self.layer.set_drawn_levels(low, high)

    def _released(self):
        self.held = False
        self.redraw()

    def wheel(self, ev):
        at = self.vb.mapSceneToView(ev.scenePos()).y()
        low, high = self.layer.drawn_levels()
        factor = WHEEL_STEP ** (-ev.delta() / 120)
        self.layer.set_drawn_levels(at - (at - low) * factor, at + (high - at) * factor)
        ev.accept()


class ImageLayer(QObject):
    """The image of *plot* with its colour bar.

    The values are indexed [y, x] and drawn on bin edges. ``changed`` is
    emitted when the user changes the colours or levels.
    """

    changed = pyqtSignal()

    def __init__(self, plot):
        super().__init__()
        self.plot = plot
        self.image = pg.ImageItem(axisOrder="row-major", autoDownsample=True)
        self.mesh = None
        plot.addItem(self.image)
        # These are the drawn values, which are log10 of the data on a log scale.
        self.values = None
        self.edges = None
        self.range = (0.0, 1.0)
        self.colormap_name, self.reversed = "viridis", False
        self.transparent_low = False
        self.cmap = colormap(self.colormap_name)
        self.log, self.mode = False, "always"
        # The levels are in the unit of the values, also on a log scale.
        self.levels = (0.0, 1.0)
        # If this is True the next image sets the levels.
        self.relevel = False
        self.colorbar = ColorBar(self)
        plot.layout.addItem(self.colorbar, 2, 5)
        plot.layout.setColumnFixedWidth(4, 5)

    def set_image(self, values, x_edges, y_edges):
        values = np.asarray(values, dtype=float)
        self.values = log_values(values) if self.log else values
        self.edges = x_edges, y_edges
        finite = self.values[np.isfinite(self.values)]
        self.range = (finite.min(), finite.max()) if finite.size else (0.0, 1.0)
        if self.follow or self.relevel:
            self.levels, self.relevel = self.auto_levels(), False
        self.draw()

    @property
    def follow(self):
        """Return True if each new image sets the levels."""
        return self.mode == "always"

    def draw(self):
        if self.values is None:
            return
        shown = self.values
        levels = self.drawn_levels()
        if self.transparent_low:
            shown = np.where(shown > levels[0], shown, np.nan)
        x, y = self.edges
        if _even(x) and _even(y):
            item = self.image
            item.setImage(shown, autoLevels=False)
            item.setRect(x[0], y[0], x[-1] - x[0], y[-1] - y[0])
        else:
            if self.mesh is None:
                self.mesh = pg.PColorMeshItem(enableAutoLevels=False)
                self.plot.addItem(self.mesh)
            item = self.mesh
            item.setData(*np.meshgrid(x, y), shown)
        self.image.setVisible(item is self.image)
        if self.mesh is not None:
            self.mesh.setVisible(item is self.mesh)
        item.setColorMap(self.cmap)
        item.setLevels(levels)
        self.colorbar.redraw()

    def auto_levels(self):
        """Return automatic levels, centred on 0 for a diverging colormap."""
        low, high = auto_levels(self.values)
        if self.log:
            return 10**low, 10**high
        if self.colormap_name in COLORMAP_GROUPS["Diverging"] and low < 0 < high:
            low, high = -max(-low, high), max(-low, high)
        return low, high

    def drawn_levels(self):
        """Return the levels as drawn, which is log10 of them on a log scale.

        On a log scale a level at or below 0 becomes the lowest or highest
        drawn value of the image.
        """
        if not self.log:
            return self.levels
        logs = log_values(np.array(self.levels, dtype=float))
        return tuple(
            float(v) if np.isfinite(v) else r
            for v, r in zip(logs, self.range, strict=True)
        )

    def _set(self, **settings):
        self.__dict__.update(settings)
        self.cmap = colormap(self.colormap_name, self.reversed)
        if self.follow and self.values is not None:
            self.levels = self.auto_levels()
        self.draw()
        self.changed.emit()

    def set_levels(self, low, high):
        """Set the levels by hand and keep them for new images."""
        self._set(mode="manual", levels=(float(low), float(high)))

    def _typed_levels(self, low, high):
        if high > low:
            self.set_levels(low, high)

    def set_drawn_levels(self, low, high):
        """Set the levels by hand in drawn units, which are log10 on a log scale."""
        self.set_levels(*((10**low, 10**high) if self.log else (low, high)))

    def set_mode(self, mode):
        """Choose which images set the levels.

        With ``always`` every image sets them, with ``once`` only the next image
        does and with ``manual`` the levels stay as they are.
        """
        self._set(mode=mode, relevel=mode == "once")

    def scale_now(self):
        self._set(levels=self.auto_levels())

    def set_colormap(self, name):
        if name not in COLORMAPS:
            raise ValueError(f"unknown colormap: {name}")
        self._set(colormap_name=name)

    def set_reversed(self, on):
        self._set(reversed=on)

    def set_transparent_low(self, on):
        """Hide values at or below the low level, such as empty bins."""
        self._set(transparent_low=on)

    def set_log(self, log):
        """Colour by log10 of the values, starting with the next image."""
        if log != self.log:
            self.log = log
            self.colorbar.axis.setLogMode(log)

    def add_menu_entries(self, menu):
        """Add the colour entries. The plot adds the "Log scale" entry itself."""
        # Show the levels to 0.1 % of their span.
        span = abs(np.subtract(*self.levels))
        digits = 3 - int(np.floor(np.log10(span))) if 0 < span < np.inf else 3
        levels = zip(("Low", "High"), np.round(self.levels, digits), strict=True)
        add_widget(menu, NumberForm(levels, self._typed_levels))
        menu.addAction("Scale to this image").triggered.connect(self.scale_now)
        menu.addSeparator()
        radio_entries(menu, LEVEL_MODES, self.mode, self.set_mode)
        menu.addSeparator()
        maps = menu.addMenu(f"Colormap: {self.colormap_name}")
        group = QActionGroup(maps)
        for kind, names in COLORMAP_GROUPS.items():
            maps.addSection(kind)
            for name in names:
                buildMenuEntryAction(maps, name, "matplotlib")
                entry = group.addAction(maps.actions()[-1])
                # The text is not displayed because the swatch shows the name.
                entry.setText(name)
                entry.setCheckable(True)
                entry.triggered.connect(lambda _c, n=name: self.set_colormap(n))
                if name == self.colormap_name:
                    # A swatch shows no check mark, so add one by hand.
                    entry.setChecked(True)
                    entry.defaultWidget().layout().addWidget(QLabel("✓"))
        check_action(menu, "Reversed", self.reversed, self.set_reversed)
        check_action(menu, "Hide ≤ Low", self.transparent_low, self.set_transparent_low)

    def state(self):
        return dict(
            colormap=self.colormap_name,
            reversed=self.reversed,
            transparent_low=self.transparent_low,
            mode=self.mode,
            levels=list(self.levels),
        )

    def restore(self, state):
        if state.get("colormap") in COLORMAPS:
            self.colormap_name = state["colormap"]
        self.reversed = bool(state.get("reversed", False))
        self.transparent_low = bool(state.get("transparent_low", False))
        levels = state.get("levels")
        # Levels or a mode of the wrong kind, as in a damaged file, are left out.
        valid = isinstance(levels, list) and len(levels) == 2
        valid = valid and all(isinstance(v, (int, float)) for v in levels)
        mode = state.get("mode", "always")
        self.mode = mode if valid and mode in LEVEL_MODES else "always"
        if not self.follow:
            self.levels = tuple(levels)
        self.relevel = self.mode == "once"
        self.cmap = colormap(self.colormap_name, self.reversed)
