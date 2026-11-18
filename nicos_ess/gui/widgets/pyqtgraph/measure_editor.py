"""The user measures the image of a plot with a crosshair, a box or a line.

Unlike ROIs, measurements are only shown in the GUI and are not sent to the
data reduction. Each measurement has a label that shows the result. Clicking
the label opens a menu to edit the position and to show the statistics. The
menu of a line also lets the user enter the real length of the line, which
sets the length scale of the plot.
"""

import numpy as np
import pyqtgraph as pg
from scipy.ndimage import map_coordinates

from nicos.guisupport.qt import (
    QApplication,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QObject,
    Qt,
    QTimer,
    QWidget,
    pyqtSignal,
    sip,
)
from nicos_ess.gui.widgets.pyqtgraph.frame_format import (
    edges_of,
    format_position,
    is_pixels,
    with_unit,
)
from nicos_ess.gui.widgets.pyqtgraph.plot_parts import (
    FIELD_WIDTH,
    NumberForm,
    add_widget,
    number_field,
    numbers,
    radio_entries,
)
from nicos_ess.gui.widgets.pyqtgraph.profiles import finite_mean
from nicos_ess.gui.widgets.pyqtgraph.roi import LineROI, PlotROI
from nicos_ess.gui.widgets.pyqtgraph.theme import (
    ATTENTION,
    CROSS_COLOR,
    CROSS_EDGE,
    CROSS_HOOVER_COLOR,
    LINE_ROI_HANDLE_COLOR_LEFT,
    LINE_ROI_HANDLE_COLOR_RIGHT,
    LINE_ROI_HOOVER_COLOR,
    ROI_COLOR,
    ROI_HOOVER_COLOR,
    TICK_SCALE,
    scaled_font,
)

PENS = dict(
    pen=pg.mkPen(ROI_COLOR, width=3), hoverPen=pg.mkPen(ROI_HOOVER_COLOR, width=3)
)
# The result is updated this many times per second while a shape is dragged.
LIVE_RATE = 20
# A result wider than this share of the view is shortened.
LABEL_SHARE = 0.9
# Distance in label heights between the top of a shape and its label.
LIFT = 1.4
LABEL_TIP = (
    "Click the label or right-click the shape to see the position and the"
    " statistics or to remove the measurement"
)


def _pixel(edges, values):
    """Convert *values* on the axis to fractional bin indices.

    Bin i spans the indices i to i + 1.
    """
    index = np.arange(len(edges), dtype=float)
    if edges[-1] < edges[0]:
        return np.interp(values, edges[::-1], index[::-1])
    return np.interp(values, edges, index)


def _bins_within(edges, low, high):
    """Return the range [first, stop) of the bins with centres in low to high.

    The range always holds at least one bin.
    """
    low, high = sorted(_pixel(edges, [low, high]) - 0.5)
    count = len(edges) - 1
    first = min(int(np.ceil(low - 1e-9)), count - 1)
    return first, min(max(int(np.floor(high + 1e-9)) + 1, first + 1), count)


def stats(values):
    """Return the statistics of the finite *values* as a dict."""
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    shown = finite if finite.size else np.array([np.nan])
    return {
        "mean": shown.mean(),
        "std": shown.std(),
        "min": shown.min(),
        "max": shown.max(),
        "sum": finite.sum(),
        "size": f"{finite.size:,} bins",
    }


class Measure:
    """Base class for a measurement on the image of *editor*.

    Each kind of measurement is a subclass. A subclass creates the plot items,
    reads and moves the points, names the position fields and measures the
    image. After `update` the label text is in ``text`` and the statistics are
    in ``stats``. The profiles to draw next to the image are in ``profiles``
    as (strip, positions, values) tuples.
    """

    kind = tool = color = tip = ""
    ends = None  # These colours mark the two ends of the profile.
    unit = ""  # This is the unit of the distance along the profile.
    # The first signal fires during a drag and the second one when it ends.
    signals = ("sigRegionChanged", "sigRegionChangeFinished")

    def __init__(self, editor):
        self.editor = editor
        self.text, self.stats, self.profiles = "", {}, []
        self.items = self.make_items()
        live, done = self.signals
        # The signal proxies stop working when they are garbage collected.
        self.proxies = []
        for item in self.items:
            getattr(item, done).connect(self.update)
            item.sigClicked.connect(self.clicked)
            if isinstance(item, pg.ROI):
                item.setAcceptedMouseButtons(Qt.MouseButton.RightButton)
            self.proxies.append(
                pg.SignalProxy(
                    getattr(item, live), rateLimit=LIVE_RATE, slot=self.follow
                )
            )
        self.label = pg.TextItem(
            color=ATTENTION, fill=pg.mkBrush(255, 255, 255, 220), anchor=(0, 1)
        )
        self.label.setFont(scaled_font(TICK_SCALE))
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label.setToolTip(LABEL_TIP)
        self.label.setZValue(1000)  # The label is drawn above the shapes.
        # This holds the widest label so far for the full text and for the
        # short text.
        self.widest = {}

    def quietly(self, points):
        """Move to *points* without emitting any signals."""
        for item in self.items:
            item.blockSignals(True)
        self.move(points)
        for item in self.items:
            item.blockSignals(False)

    def set_points(self, points):
        self.quietly(points)
        self.update()

    def place(self, numbers):
        """Move to the numbers that were typed into the position fields."""
        self.set_points(list(zip(numbers[::2], numbers[1::2], strict=True)))

    def regrid(self, old, new):
        """Stay on the same pixels when the grid changes from *old* to *new*."""
        self.quietly(
            [new.pixel_to_world(*old.world_to_pixel(*p)) for p in self.points()]
        )

    def label_place(self, points):
        """Return the x in the middle of the shape and the y of the top edge."""
        xs, ys = zip(*points, strict=True)
        return np.mean(xs), min(ys) if self.editor.plot.vb.yInverted() else max(ys)

    def short(self):
        """Return the first figure of the result for when the full text is too wide."""
        return self.text.split(" · ")[0]

    def value_unit(self):
        return self.editor.image.layer.colorbar.axis.labelText

    def snap(self, xe, ye):
        """Snap to the bins with edges *xe* and *ye* if this kind supports it."""

    def menu_entries(self, menu):
        """Add the entries that are specific to this kind to the menu."""

    def clicked(self, _item, ev):
        """A right-click on the shape opens the same menu as a click on the label."""
        if ev.button() == Qt.MouseButton.RightButton:
            ev.accept()
            self.editor.open_menu(self.kind, ev.screenPos().toPoint())

    def follow(self, _signal_args=None):
        # The rate limit delays this update, so the plot can be deleted by then.
        if not sip.isdeleted(self.label):
            self.update(live=True)

    def update(self, *_signal_args, live=False):
        """Measure the current image and show the result.

        Set *live* while an item is dragged. A live update does not snap to
        bins and adds no profile strips, because new strips would move the
        image under the pointer.
        """
        editor, image = self.editor, self.editor.image
        if image is None or image.data is None:
            return
        xe, ye = edges_of(image.axis("x")), edges_of(image.axis("y"))
        done = not live and editor.drawing != self.kind
        if done:
            self.snap(xe, ye)
        points = self.points()
        self.measure(image.data, xe, ye, points)
        self.label.setPos(*self.label_place(points))
        editor.fit_labels()
        profiles = editor.profiles
        if done or any(key == self.kind for _strip, key in profiles.profiles):
            for strip, positions, curve in self.profiles:
                profiles.set(
                    strip, self.kind, positions, curve, self.color, self.ends, self.unit
                )
        if editor.menu_follows is not None:
            editor.menu_follows()


class _EdgedLine(pg.InfiniteLine):
    """An infinite line with a dark edge so it stays visible on any colormap."""

    def paint(self, p, *args):
        left, right = self._endPoints
        p.setPen(pg.mkPen(CROSS_EDGE, width=self.currentPen.widthF() + 2))
        p.drawLine(pg.Point(left, 0), pg.Point(right, 0))
        super().paint(p, *args)


class Crosshair(Measure):
    """The crosshair has two lines across the image that the user drags one at
    a time.
    """

    kind, tool, color = "crosshair", "Crosshair", CROSS_HOOVER_COLOR
    tip = "Click on an image to see the value there"
    signals = ("sigPositionChanged", "sigPositionChangeFinished")

    def short(self):
        return self.text.split(": ")[-1]

    def make_items(self):
        pens = dict(
            pen=pg.mkPen(CROSS_COLOR, width=2),
            hoverPen=pg.mkPen(CROSS_HOOVER_COLOR, width=3),
            movable=True,
        )
        return _EdgedLine(angle=90, **pens), _EdgedLine(angle=0, **pens)

    def points(self):
        return [(self.items[0].value(), self.items[1].value())]

    def move(self, points):
        for item, value in zip(self.items, points[0], strict=True):
            item.setValue(value)

    def fields(self, x, y):
        (px, py), *_ = self.points()
        return [(x, px), (y, py)]

    def measure(self, values, xe, ye, points):
        (x, y), image = points[0], self.editor.image
        column = min(int(_pixel(xe, x)), len(xe) - 2)
        row = min(int(_pixel(ye, y)), len(ye) - 2)
        value = values[row, column]
        where = ", ".join(  # This matches the hover box in frame_format.
            f"{image.axis_label(a)} {format_position(image.axis(a), i)}"
            for a, i in (("x", column), ("y", row))
        )
        self.text = f"{where}: {with_unit(value, self.value_unit())}"
        self.stats = {"value": value}
        for name, line in (("row", values[row]), ("column", values[:, column])):
            self.stats |= {f"{name} {k}": v for k, v in stats(line).items()}
        self.profiles = [("x", xe, values[row]), ("y", ye, values[:, column])]


class Box(Measure):
    kind, tool, color = "box", "Box", ROI_HOOVER_COLOR
    tip = "Drag on an image to see the sum, mean and maximum inside the box"

    def make_items(self):
        return (PlotROI((1, 1), **PENS),)

    def points(self):
        (x0, y0), (w, h) = self.items[0].pos(), self.items[0].size()
        return [(x0, y0), (x0 + w, y0 + h)]

    def move(self, points):
        (x0, y0), (x1, y1) = points
        self.items[0].setPos((min(x0, x1), min(y0, y1)), finish=False)
        self.items[0].setSize((abs(x1 - x0), abs(y1 - y0)), finish=False)

    # On pixel axes the fields show the first and the last pixel.
    def _halves(self):
        hx, hy = (0.5 * is_pixels(self.editor.image.axis(a)) for a in "xy")
        return np.array([hx, -hx, hy, -hy])

    def place(self, numbers):
        x0, x1, y0, y1 = np.subtract(numbers, self._halves())
        super().place([x0, y0, x1, y1])  # The base class wants x, y pairs.

    def fields(self, x, y):
        (x0, y0), (x1, y1) = self.points()
        names = [f"{x} from", f"{x} to", f"{y} from", f"{y} to"]
        return list(zip(names, [x0, x1, y0, y1] + self._halves(), strict=True))

    def snap(self, xe, ye):
        """Move the edges of the box out to the bins with centres inside it."""
        (x0, y0), (x1, y1) = self.points()
        (c0, c1), (r0, r1) = _bins_within(xe, x0, x1), _bins_within(ye, y0, y1)
        snapped = [(xe[c0], ye[r0]), (xe[c1], ye[r1])]
        if not np.allclose(snapped, [(x0, y0), (x1, y1)]):
            self.quietly(snapped)

    def measure(self, values, xe, ye, points):
        (x0, y0), (x1, y1), image = *points, self.editor.image
        (c0, c1), (r0, r1) = _bins_within(xe, x0, x1), _bins_within(ye, y0, y1)
        inside = values[r0:r1, c0:c1]
        self.stats = stats(inside)
        figures = [("Σ", "sum"), ("mean", "mean")][:: 1 if image.counts else -1]
        self.text = " · ".join(  # The first figure is the one in the title.
            f"{name} {with_unit(self.stats[key], self.value_unit())}"
            for name, key in (*figures, ("max", "max"))
        )
        self.profiles = [
            ("x", xe[c0 : c1 + 1], finite_mean(inside, 0)),
            ("y", ye[r0 : r1 + 1], finite_mean(inside, 1)),
        ]


class Line(Measure):
    """The line has a width, and the profile is the mean across the width."""

    kind, tool, color = "line", "Line", LINE_ROI_HOOVER_COLOR
    tip = "Drag on an image to see the length of the line and the mean along it"
    # The ends of the profile get the colours of the handles.
    ends = LINE_ROI_HANDLE_COLOR_LEFT, LINE_ROI_HANDLE_COLOR_RIGHT

    def make_items(self):
        xe, ye = (edges_of(self.editor.image.axis(a)) for a in "xy")
        width = min(abs(xe[1] - xe[0]), abs(ye[1] - ye[0]))
        return (LineROI((0, 0), (1, 0), width),)

    def points(self):
        return [(p.x(), p.y()) for p in self.items[0].get_pos()]

    def move(self, points):
        self.items[0].set_pos(*points)

    def fields(self, x, y):
        names = [f"{end} {a}" for end in ("start", "end") for a in (x, y)]
        values = [*np.ravel(self.points()), self.items[0].get_width()]
        return list(zip([*names, "width"], values, strict=True))

    def place(self, numbers):
        self.items[0].set_pos(numbers[:2], numbers[2:4], abs(numbers[4]))
        self.set_points(self.points())

    def regrid(self, old, new):
        """Keep the line on the same pixels and keep the width in pixels."""
        (x0, y0), (x1, y1) = self.points()
        normal = np.array([y0 - y1, x1 - x0]) / (np.hypot(x1 - x0, y1 - y0) or 1)
        side = np.array([x0, y0]) + self.items[0].get_width() * normal
        moved = [new.pixel_to_world(*old.world_to_pixel(*p)) for p in ((x0, y0), side)]
        super().regrid(old, new)
        self.items[0].set_pos(*self.points(), float(np.hypot(*np.subtract(*moved))))

    def length(self):
        """Return the length of the line as (value, unit) in the length scale.

        Return None when x and y are different quantities.
        """
        image = self.editor.image
        if not image.same_space():
            return None
        (x0, y0), (x1, y1) = self.points()
        length = float(np.hypot(x1 - x0, y1 - y0))
        factor, unit = self.editor.length_scale or (1.0, image.axis_unit("x") or "px")
        return length * factor, unit

    def measure(self, values, xe, ye, points):
        """Sample the image along the line and across the width of the line.

        There is about one sample per bin in each direction, and the samples
        are averaged across the width. The values are interpolated linearly
        between bin centres.
        """
        (x0, y0), (x1, y1) = points
        width = self.items[0].get_width()
        normal = np.array([y0 - y1, x1 - x0]) / (np.hypot(x1 - x0, y1 - y0) or 1)

        # This returns the number of bins that a step of (dx, dy) from (x, y)
        # crosses.
        def bins(dx, dy, x=x0, y=y0):
            return np.hypot(
                *np.diff(_pixel(xe, [x, x + dx])), *np.diff(_pixel(ye, [y, y + dy]))
            )

        along = np.linspace(0.0, 1.0, max(2, int(np.ceil(bins(x1 - x0, y1 - y0))) + 1))
        side = width * normal
        count = max(1, int(np.ceil(bins(*side, x0 - side[0] / 2, y0 - side[1] / 2))))
        # Each sample sits in the middle of its slice of the width, so a line
        # three bins wide samples the centres of those three bins.
        across = ((np.arange(count) + 0.5) / count - 0.5) * width
        xs = x0 + along * (x1 - x0) + across[:, None] * normal[0]
        ys = y0 + along * (y1 - y0) + across[:, None] * normal[1]
        samples = map_coordinates(
            values,
            [_pixel(ye, ys) - 0.5, _pixel(xe, xs) - 0.5],
            order=1,
            mode="nearest",
        )
        inside = (
            (xs >= xe.min()) & (xs <= xe.max()) & (ys >= ye.min()) & (ys <= ye.max())
        )
        samples = finite_mean(np.where(inside, samples, np.nan), 0)
        self.stats = stats(samples)
        del self.stats["sum"]  # A sum of interpolated samples means nothing.
        self.text = f"mean {with_unit(self.stats['mean'], self.value_unit())}"
        if (length := self.length()) is not None:
            self.stats["length"] = with_unit(*length)
            self.text = f"length {self.stats['length']} · {self.text}"
            along, self.unit = along * length[0], length[1]
        else:  # x and y are different quantities, so measure in pixels.
            along, self.unit = along * bins(x1 - x0, y1 - y0), "px"
        self.profiles = [("line", along, samples)]

    def label_place(self, points):
        """Put the label at the end of the line that is higher on screen."""
        top = super().label_place(points)[1]
        return next(x for x, y in points if y == top), top

    def menu_entries(self, menu):
        if self.length() is not None:
            _add_scale_entries(menu, self.editor, self)


KINDS = {kind.kind: kind for kind in (Crosshair, Box, Line)}
TOOLS = {kind: cls.tool for kind, cls in KINDS.items()}


class MeasureEditor(QObject):
    """The editor keeps the measurements on an image, at most one of each kind.

    `attach` moves the measurements to a new `FrameImage` and its
    `SideProfiles`, and `detach` takes them off again. ``placed`` is emitted
    when a measurement was drawn and ``scale_changed`` when ``length_scale``
    changes. The length scale is a (factor, unit) pair. A length in the unit
    of the image times the factor gives the length in that unit.
    """

    placed = pyqtSignal()
    scale_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.plot = self.image = self.profiles = self.grid = None
        self.tools = {}
        self.drawing = None  # The kind that is being drawn right now.
        self.length_scale = None
        self.menu_follows = None  # This callback refreshes the open menu.
        # The menu opens after the double-click interval, so that a double-click
        # on a label can be told apart from a click.
        self._menu_timer = QTimer(singleShot=True)
        self._menu_timer.setInterval(QApplication.doubleClickInterval())
        self._menu_timer.timeout.connect(lambda: self.open_menu(*self._menu_at))
        self._menu_at = None

    def detach(self):
        for measure in self.tools.values():
            for item in (*measure.items, measure.label):
                self.plot.removeItem(item)
        self.plot.vb.sigTransformChanged.disconnect(self.fit_labels)
        self.plot = self.image = self.profiles = None

    def attach(self, plot, image, profiles):
        self.plot, self.image, self.profiles = plot, image, profiles
        for measure in self.tools.values():
            self._add(measure)
        image.grid_changed.connect(self._regrid)
        image.image_changed.connect(self._update_all)
        plot.vb.sigTransformChanged.connect(self.fit_labels)

    def _regrid(self, grid):
        """Keep the measurements on their pixels when the axes change."""
        if self.grid is not None:
            for measure in self.tools.values():
                measure.regrid(self.grid, grid)
        self.grid = grid

    def _add(self, measure):
        # Auto-range would move the image while drawing if it used these items.
        for item in (*measure.items, measure.label):
            self.plot.addItem(item, ignoreBounds=True)

    def _update_all(self, _data=None):
        for measure in self.tools.values():
            measure.update()

    def measure_at(self, x, y):
        """Put the crosshair at (x, y). Return False if there is no image."""
        return self.measure_between("crosshair", pg.Point(x, y), pg.Point(x, y), True)

    def measure_between(self, kind, start, end, done):
        """Draw a box or line from *start* to *end*.

        Return False if there is no image. The profiles are only drawn when
        *done* is true, because adding their strips would move the image under
        the pointer.
        """
        if self.image is None or self.image.data is None:
            return False
        self.drawing = None if done else kind
        if kind not in self.tools:
            self.tools[kind] = KINDS[kind](self)
            self._add(self.tools[kind])
        points = [(start.x(), start.y()), (end.x(), end.y())]
        if done:
            self.tools[kind].set_points(points)
            self.placed.emit()
        else:
            self.tools[kind].move(points)
        return True

    def remove(self, kind):
        measure = self.tools.pop(kind)
        if self.plot is not None:
            for item in (*measure.items, measure.label):
                self.plot.removeItem(item)
            self.profiles.drop(kind)  # The profiles of the full image stay.

    def clear(self):
        for kind in list(self.tools):
            self.remove(kind)

    def set_length_scale(self, factor, unit=None):
        self.length_scale = None if factor is None else (float(factor), unit)
        if "line" in self.tools:
            self.tools["line"].update()
        self.scale_changed.emit()

    def label_at(self, scene_pos):
        """Return the kind of measurement whose label is at *scene_pos*."""
        if self.image is None:
            return None
        for kind, measure in self.tools.items():
            label = measure.label
            if label.isVisible() and label.sceneBoundingRect().contains(scene_pos):
                return kind
        return None

    def open_menu(self, kind, screen_pos):
        measure_menu(self, kind).exec(screen_pos)

    def open_menu_later(self, kind, screen_pos):
        """Open the menu of *kind* after the double-click interval unless
        `cancel_menu` is called first."""
        self._menu_at = (kind, screen_pos)
        self._menu_timer.start()

    def cancel_menu(self):
        self._menu_timer.stop()

    def fit_labels(self):
        """Place each label above its shape, inside the view and off the others.

        A label shows only the first figure when the full text is too wide.
        A label never gets narrower than it was, and near the right edge of
        the view it moves to the left of its shape.
        """
        vb, taken = self.plot.vb, []
        (low, high), room = vb.viewRange()[0], LABEL_SHARE * vb.width()
        view = vb.sceneBoundingRect()
        for measure in self.tools.values():
            label = measure.label
            side = float(np.clip((label.pos().x() - low) / (high - low or 1), 0, 1))
            label.setTextWidth(-1)
            label.setText(measure.text)
            short = label.textItem.boundingRect().width() > room
            if short:
                label.setText(measure.short())
            width = label.textItem.boundingRect().width()
            widest = measure.widest[short] = max(measure.widest.get(short, 0), width)
            label.setTextWidth(max(width, min(widest, room)))
            for lift in LIFT + np.array([0, 1, -2, 2, -3]):  # Try above, then below.
                label.setAnchor((side, lift))
                rect = label.sceneBoundingRect()
                if view.contains(rect) and not any(rect.intersects(t) for t in taken):
                    break
            taken.append(label.sceneBoundingRect())

    def menu_entries(self, menu, choose, armed):
        """Add the Measure submenu with the *armed* tool checked.

        Choosing a tool calls *choose* with the kind of that tool.
        """
        sub = menu.addMenu("Measure")
        radio_entries(sub, TOOLS, armed, choose)
        sub.addAction("Clear", self.clear).setEnabled(bool(self.tools))


def statistics(measure):
    """Return the statistics of a measurement as (name, text) rows."""
    unit = measure.value_unit()
    return [
        (name, value if isinstance(value, str) else with_unit(value, unit))
        for name, value in measure.stats.items()
    ]


def _position_rows(measure):
    """Return the position of a measurement as (field name, value) rows."""
    image = measure.editor.image
    x, y = (f"{image.axis_label(a)} ({image.axis_unit(a)})" for a in "xy")
    return measure.fields(x.replace(" ()", ""), y.replace(" ()", ""))


def measure_menu(editor, kind):
    """Return the menu for the measurement of *kind*.

    While the menu is open, it updates when the user types a position, moves
    the measurement or when a new image arrives.
    """
    measure = editor.tools[kind]
    menu = QMenu()
    form = NumberForm(_position_rows(measure), lambda *numbers: measure.place(numbers))
    form.setObjectName("position")
    add_widget(menu, form)
    menu.addSection("Statistics")
    table = QWidget(objectName="statistics")
    layout = QFormLayout(table)
    layout.setContentsMargins(10, 0, 10, 4)
    labels = {}
    for name, text in statistics(measure):
        labels[name] = QLabel(text)
        labels[name].setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addRow(name, labels[name])
    add_widget(menu, table)
    menu.addAction("Copy statistics").triggered.connect(
        lambda: QApplication.clipboard().setText(
            "\n".join(f"{name}\t{text}" for name, text in statistics(measure))
        )
    )
    measure.menu_entries(menu)
    menu.addSeparator()
    menu.addAction("Remove", lambda: editor.remove(kind))

    def follow():
        form.show_values([value for _name, value in _position_rows(measure)])
        for name, text in statistics(measure):
            if name in labels:
                labels[name].setText(text)

    editor.menu_follows = follow
    menu.destroyed.connect(lambda: setattr(editor, "menu_follows", None))
    return menu


def _add_scale_entries(menu, editor, line):
    """Add fields that set the length scale of the plot from a line.

    The user enters the real length of a line drawn across something of
    known size. This is the only length scale a pixel image can have.
    """
    menu.addSection("Length scale")
    row = QWidget(objectName="length scale")
    form = QFormLayout(row)
    form.setContentsMargins(10, 0, 10, 4)
    scale = editor.length_scale
    length = number_field(line.length()[0] if scale else None)
    unit = QLineEdit(scale[1] if scale else "mm")
    unit.setMaximumWidth(FIELD_WIDTH)
    form.addRow("This line is", length)
    form.addRow("in", unit)

    def apply():
        typed = numbers([length])
        drawn = line.length()[0] / (editor.length_scale or (1.0,))[0]
        if typed and typed[0] > 0 and drawn > 0 and unit.text().strip():
            editor.set_length_scale(typed[0] / drawn, unit.text().strip())

    length.editingFinished.connect(apply)
    unit.editingFinished.connect(apply)
    add_widget(menu, row)
    if scale:
        menu.addAction("Forget the length scale", lambda: editor.set_length_scale(None))
