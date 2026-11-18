"""The profiles of an image are drawn in strips along the left and bottom edges.

The y profile is drawn left of the image and the x profile below it. Each
strip is linked to the image along one axis. A profile along a drawn line
has no image axis to share, so it gets a small plot in the corner between
the strips, or below the image if there are no strips. The values always
grow away from the image. They grow leftwards in the y strip and downwards
in the x strip and in the line plot, which shares the row of the x strip.
The strips are cells of the layout around the `PlotItem` of the image, and
their margins line them up with the view box. While the strips are shown,
the image axes are drawn outside them instead of the plot axes.

    layout:  col 0                 col 1
      row 0              y values
      row 1  y ticks     y profile PlotItem: image, colour bar
      row 2  line values line      x profile, x values
                         distance  x ticks
"""

import numpy as np
import pyqtgraph as pg

from nicos.guisupport.qt import QGraphicsRectItem, QObject, Qt, pyqtSignal
from nicos_ess.gui.widgets.pyqtgraph import frame_format as fmt
from nicos_ess.gui.widgets.pyqtgraph.plot_parts import settle_layout
from nicos_ess.gui.widgets.pyqtgraph.theme import (
    LINE_WIDTH,
    CompactAxisItem,
    curve_color,
    fix_axis_room,
    label_room,
)

# The automatic strip depth is a share of the smaller side of the plot,
# clipped to a range in px. Compact plots get thinner strips.
STRIP_DEPTH, COMPACT_DEPTH = (0.1, 30, 80), (0.1, 24, 80)
# A dragged depth is also a share of the smaller side and at least DRAGGED_MIN
# px. Both strips together never take more than 2 * MAX_SHARE of that side.
DRAGGED_MIN, MAX_SHARE = 24, 0.15
LARGE = 1e6  # A size in px this large acts as no limit.
# The grip is 6 px wide and lights up like the splitters of the grid.
GRIP, GRIP_BRUSH = 6, pg.mkBrush("#c9d6e3")
GRIP_TIP = (
    "Drag to make the profiles deeper or shallower.\n"
    "Double-click to restore the automatic size."
)
# The readout shows these names instead of the profile key.
PROFILE_NAMES = {"full": "mean"}
PADDING = 0.05  # The padding is a fraction of the value span.


def finite_mean(values, axis):
    """Return the mean of the finite values along *axis*.

    The mean is NaN where there are no finite values.
    """
    finite = np.isfinite(values)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(finite, values, 0).sum(axis) / finite.sum(axis)


def _value_range(values, log):
    values = values[np.isfinite(values)]
    if log:
        values = np.log10(values[values > 0])
    if not values.size:
        return 0.0, 1.0
    low, high = float(values.min()), float(values.max())
    return (low, high) if high > low else (low - 0.5, high + 0.5)


class _StripAxis(CompactAxisItem):
    """This axis labels only the ``ends`` of the data when fewer than two
    ticks fit.

    If both end labels do not fit either, the axis shows only the top one or
    none. Labels are kept inside the axis length, and the last label gets the
    ``unit`` if one is set.
    """

    ends = unit = None

    def __init__(self, orientation):
        super().__init__(orientation)
        # Labels may reach 60 px past the ends because generateDrawSpecs moves
        # them back inside.
        self.setStyle(hideOverlappingLabels=60)

    def tickValues(self, minVal, maxVal, size):
        ticks = super().tickValues(minVal, maxVal, size)
        low, high = sorted((minVal, maxVal))
        major = [v for v in ticks[0][1] if low <= v <= high]
        if len(major) >= 2 and size:
            gap = np.diff(major).min() * size / (high - low)
            labels = self.tickStrings(major, 1, ticks[0][0])
            if gap >= max(label_room(self, t) for t in labels):
                return ticks
        low, high = self.ends or (low, high)
        return self._end_ticks(low, high, size)

    def _end_ticks(self, low, high, size):
        """Return ticks at both ends, at the top end only, or none, so that
        the labels fit in *size* px."""
        # A label at the end of the axis needs only half the usual gap. The
        # first step tries one more digit.
        for step in ((high - low) / 10, high - low):
            labels = self.tickStrings([low, high], 1, step)
            rooms = [label_room(self, t) - label_room(self, "") / 2 for t in labels]
            if sum(rooms) <= size:
                return [(step, [low, high])]
        return [(step, [high])] if rooms[1] <= size else []

    def tickStrings(self, values, scale, spacing):
        strings = super().tickStrings(values, scale, spacing)
        if self.unit and strings:
            strings[-1] += f" {self.unit}"
        return strings

    def generateDrawSpecs(self, p):
        specs = super().generateDrawSpecs(p)
        size = self.size()
        for rect, _flags, _text in specs[2]:
            if self.orientation in ("top", "bottom"):
                rect.moveLeft(np.clip(rect.left(), 0, size.width() - rect.width()))
            else:
                rect.moveTop(np.clip(rect.top(), 0, size.height() - rect.height()))
        return specs


def _fix_size(item, width, height):
    """Fix the width and height of *item*, where None lets the size grow.

    A top or bottom axis gets only the width, and a left or right axis gets
    only the height.
    """
    side = getattr(item, "orientation", None)
    if side in (None, "top", "bottom"):
        item.setMinimumWidth(width or 0)
        item.setMaximumWidth(width or LARGE)
    if side in (None, "left", "right"):
        item.setMinimumHeight(height or 0)
        item.setMaximumHeight(height or LARGE)


class _Grip(QGraphicsRectItem):
    """The grip is a splitter on the edge between a strip and the image.

    Dragging the edge makes the strips deeper and the image smaller. A
    double-click restores the automatic depth.
    """

    def __init__(self, strip):
        super().__init__(strip)
        self.strip, self.vertical = strip, strip.vertical
        self.setPen(pg.mkPen(None))
        self.setZValue(1e9)
        self.setToolTip(GRIP_TIP)
        cursor = Qt.CursorShape
        self.setCursor(cursor.SizeHorCursor if self.vertical else cursor.SizeVerCursor)
        strip.sigResized.connect(self._fit)

    def _fit(self):
        rect = self.strip.rect()
        # The grip sits on the edge that touches the image.
        if self.vertical:
            self.setRect(rect.right() - GRIP, rect.top(), GRIP, rect.height())
        else:
            self.setRect(rect.left(), rect.top(), rect.width(), GRIP)

    def hoverEvent(self, ev):
        if not ev.isExit():
            ev.acceptDrags(Qt.MouseButton.LeftButton)
            ev.acceptClicks(Qt.MouseButton.LeftButton)
        self.setBrush(pg.mkBrush(None) if ev.isExit() else GRIP_BRUSH)

    def mouseDragEvent(self, ev):
        ev.accept()
        profiles = self.strip.profiles
        # The image re-centres after each resize, so the edge only lands near
        # the pointer and needs a few more steps.
        for _ in range(3):
            miss = ev.scenePos() - self.sceneBoundingRect().center()
            miss = miss.x() if self.vertical else -miss.y()
            if abs(miss) < 1:
                break
            profiles.set_depth((profiles.depth + miss) / max(1, profiles.smaller()))
        if ev.isFinish():
            profiles.depth_dragged.emit()

    def mouseClickEvent(self, ev):
        if ev.double():
            ev.accept()
            self.strip.profiles.set_depth(None)
            self.strip.profiles.depth_dragged.emit()


class _Strip(pg.ViewBox):
    """A strip next to the image shows the "x", "y" or "line" profile.

    Each strip sits in its own layout ``box`` with a `_Grip` on the edge at
    the image. The x and y strips draw the image axis ``image_axis`` on their
    outer side, and the values of the y strip go above it. Clicks on a strip
    go to the plot, so the plot menu and "only this plot" still work.
    """

    def __init__(self, profiles, kind):
        super().__init__(enableMenu=False)
        self.profiles, self.kind = profiles, kind
        # The y strip is vertical, so its values run horizontally.
        self.vertical = kind == "y"
        self.setMouseEnabled(False, False)
        self.disableAutoRange()  # SideProfiles._fit sets the range.
        self.ends = None  # These are the colours of the marks at the line ends.
        self.box = pg.GraphicsLayout()
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.layout.setSpacing(0)
        # The margins that line up the strip must not stop the image from
        # shrinking.
        (self.box.setMinimumHeight if self.vertical else self.box.setMinimumWidth)(1)
        image = profiles.plot.vb
        if kind == "y":
            self.setYLink(image)
            # Values increase away from the image, and the rows run in the same
            # direction as in the image.
            self.invertX(True)
            self.invertY(image.yInverted())
            image.sigStateChanged.connect(lambda: self.invertY(image.yInverted()))
            self.image_axis = self._image_axis("left", 0, 0)
            self.box.addItem(self, 0, 1)
            self.axes = [self._axis("top")]  # SideProfiles places this axis.
        elif kind == "x":
            self.setXLink(image)
            self.invertY(True)
            self.box.addItem(self, 0, 0)
            self.axes = [self._axis("right", 0, 1)]
            self.image_axis = self._image_axis("bottom", 1, 0)
        else:
            # The line values are not inverted, so a peak points up.
            self.box.addItem(self, 0, 1)
            self.axes = [self._axis("left", 0, 0), self._axis("bottom", 1, 1)]
            # The border shows that these axes do not belong to the image.
            self.setBorder(pg.mkPen("k", width=2))
            self.marks = pg.ScatterPlotItem(size=8, pen=None)
            self.addItem(self.marks)
            self.image_axis = None
        self.grip = _Grip(self)
        self.set_compact(profiles.compact)

    def mouseClickEvent(self, ev):
        if ev.double() or ev.button() == Qt.MouseButton.RightButton:
            self.profiles.plot.vb.mouseClickEvent(ev)

    def _axis(self, side, row=None, col=None):
        axis = _StripAxis(side)
        # The bottom axis shows the distance, which is never logarithmic.
        axis.setLogMode(self.profiles.log and side != "bottom")
        fix_axis_room(axis)
        axis.linkToView(self)
        if row is not None:
            self.box.addItem(axis, row, col)
        return axis

    def _image_axis(self, side, row, col):
        axis = type(self.profiles.plot.getAxis(side))(side)
        axis.linkToView(self.profiles.plot.vb)
        self.box.addItem(axis, row, col)
        return axis

    def mirror(self):
        """Copy the label of the plot axis that this image axis replaces."""
        own = self.profiles.plot.getAxis(self.image_axis.orientation)
        self.image_axis.setLabel(own.labelText, own.labelUnits)
        self.image_axis.integers = own.integers
        self.image_axis.showLabel(own.label.isVisibleTo(own))

    def size_to(self, depth):
        """Make the strip and its axes *depth* px deep.

        The corner plot becomes *depth* px wide and high.
        """
        corner = self.kind == "line" and not self.profiles.below
        # The corner plot has no grip because the depth of the strips sets
        # the size of the corner plot.
        self.grip.setVisible(not corner)
        width = depth if self.kind == "y" or corner else None
        height = None if self.kind == "y" else depth
        for item in (self, *self.axes):
            _fix_size(item, width, height)
        if corner:
            fix_axis_room(self.axes[0])

    def align(self, before, after, ticks):
        """Line the strip up with the image.

        *before* and *after* are the room in px before and after the image
        along the strip. *ticks* holds the widths of the y ticks and of the
        corner values because the two share a column.
        """
        axis = self.axes[0]
        if self.kind == "y":
            pad = max(0.0, ticks[1] - ticks[0])
            self.box.layout.setContentsMargins(pad, before, 0, after)
        elif self.kind == "x":
            right = max(0.0, after - axis.maximumWidth())
            self.box.layout.setContentsMargins(before, 0, right, 0)
        elif self.profiles.below:
            # Below the image, the line values use the room of the image axis.
            axis.setWidth(round(before))
            self.box.layout.setContentsMargins(0, 0, after, 0)
        else:
            pad = max(0.0, ticks[0] - ticks[1])
            self.box.layout.setContentsMargins(pad, 0, 0, 0)

    def set_compact(self, compact):
        """Hide the values of the y strip in a compact plot where they do not
        fit."""
        if self.kind == "y":
            self.axes[0].setVisible(not compact)
            if compact:
                self.axes[0].setHeight(0)
            else:
                fix_axis_room(self.axes[0])


def _profile_name(key, strip):
    # A crosshair profile is named after the row or column it shows.
    if key == "crosshair":
        return "column" if strip.vertical else "row"
    return PROFILE_NAMES.get(key, key)


class SideProfiles(QObject):
    """SideProfiles draws the profiles of the `FrameImage` *image* on *plot*
    in strips next to the image.

    The strips go into cells of *layout*, which is a `pg.GraphicsLayout` with
    *plot* in row 1 and column 1. They are lined up with the view box of the
    plot. The owner calls `mirror` after changing the plot axes.

    `set` draws the profile *key*, for example "crosshair", on the strip
    *kind*. The kind is "x" or "y" for the image axes, or "line" for the
    corner between them. When there is one more position than values, the
    positions are bin edges and the profile is drawn as steps over them. A
    strip exists only while it has a profile, so an image without profiles
    keeps all of its room. ``depth_dragged`` is emitted when the user dragged
    the strip depth or restored the automatic depth.
    """

    depth_dragged = pyqtSignal()

    def __init__(self, layout, plot, image):
        super().__init__()
        self.layout, self.plot, self.image = layout, plot, image
        self.log = self.compact = self.below = False
        self.unit = ""  # The values have the same unit as the image.
        self.strips = {}  # This maps each kind to a _Strip.
        self.profiles = {}  # This maps (kind, key) to (item, positions, values).
        self.depth = None  # The strip depth is in px.
        # The dragged depth is a share of the smaller side. None means the
        # depth is automatic.
        self.dragged = None
        # The image gets all of the remaining room.
        layout.layout.setColumnStretchFactor(1, 100)
        layout.layout.setRowStretchFactor(1, 100)
        layout.geometryChanged.connect(self._size)
        plot.geometryChanged.connect(self._align)
        plot.vb.geometryChanged.connect(self._align)

    def set(self, kind, key, positions, values, color=None, ends=None, unit=""):
        """Draw the profile in the first curve colour unless *color* is given.

        If *ends* is given, the two ends of a line profile are marked in those
        colours. The positions of a line profile are distances in *unit*.
        """
        if kind not in self.strips:
            self.strips[kind] = _Strip(self, kind)
            self._place()
            self._settle()
        if (kind, key) in self.profiles:
            item = self.profiles[kind, key][0]
        else:
            item = pg.PlotDataItem(
                pen=pg.mkPen(color or curve_color(0), width=LINE_WIDTH)
            )
            item.setLogMode(kind == "y" and self.log, kind != "y" and self.log)
            self.strips[kind].addItem(item)
        positions, values = np.asarray(positions, float), np.asarray(values, float)
        self.profiles[kind, key] = (item, positions, values)
        x, y = positions, values
        if len(positions) == len(values) + 1:
            x, y = np.repeat(positions, 2)[1:-1], np.repeat(values, 2)
        item.setData(*((y, x) if kind == "y" else (x, y)), connect="finite")
        if ends is not None:
            self.strips[kind].ends = ends
        self.strips[kind].unit = unit
        self._fit(kind)

    def _fit(self, kind):
        strip = self.strips[kind]
        drawn = [v for (k, _key), v in self.profiles.items() if k == kind]
        low, high = _value_range(np.concatenate([v[2] for v in drawn]), self.log)
        strip.setRange(
            **{"xRange" if strip.vertical else "yRange": (low, high)}, padding=PADDING
        )
        strip.axes[0].ends = low, high
        if kind == "line":
            _item, positions, values = drawn[0]
            ends = positions[[0, -1]]
            # The padding leaves room for the marks.
            strip.setXRange(*ends, padding=PADDING)
            strip.axes[1].ends, strip.axes[1].unit = tuple(ends), strip.unit
            # The marks sit on the profile, or at the lower edge where the
            # profile has no finite value.
            if strip.ends is not None:
                with np.errstate(divide="ignore", invalid="ignore"):
                    y = np.log10(values[[0, -1]]) if self.log else values[[0, -1]]
                brushes = [pg.mkBrush(c) for c in strip.ends]
                strip.marks.setData(
                    ends, np.where(np.isfinite(y), y, low), brush=brushes
                )

    def pointer_rows(self, scene_pos):
        """Return the position of *scene_pos* on a strip and one row per
        profile there.

        Each row holds the colour, name, value and distance in px, like the
        rows of `FrameView.hover_at`. Outside the strips there are no rows.
        """
        on = [
            s for s in self.strips.values() if s.sceneBoundingRect().contains(scene_pos)
        ]
        if not on:
            return "", []
        strip = on[0]
        point = strip.mapSceneToView(scene_pos)
        if strip.vertical:
            at, off = point.y(), scene_pos.x()
        else:
            at, off = point.x(), scene_pos.y()
        where, rows = "", []
        for (kind, key), (item, positions, data) in self.profiles.items():
            if kind != strip.kind or not min(positions) <= at <= max(positions):
                continue
            if len(positions) == len(data) + 1:
                positions = (positions[1:] + positions[:-1]) / 2
            i = int(np.argmin(np.abs(positions - at)))
            where = self._position_text(strip, positions[i])
            value = fmt.with_unit(data[i], self.unit)
            distance = self._pointer_distance(strip, item, at, data[i], off)
            color = item.opts["pen"].color()
            rows.append((color, _profile_name(key, strip), value, distance))
        return where, rows

    def _pointer_distance(self, strip, item, at, value, off):
        """Return the distance in px across *strip* between the pointer at
        *off* and the profile *item* where it shows *value*.
        """
        y = np.log10(value) if self.log and value > 0 else value
        mark = item.mapToScene(*((y, at) if strip.vertical else (at, y)))
        return abs((mark.x() if strip.vertical else mark.y()) - off)

    def _position_text(self, strip, position):
        if strip.kind == "line":
            return f"distance {fmt.with_unit(position, strip.unit)}"
        # Show the position the same way as the image readout does.
        ax = self.image.axis(strip.kind)
        at_bin = fmt.bin_index(fmt.edges_of(ax), position)
        return f"{ax.dim} {fmt.format_position(ax, at_bin)}"

    def drop(self, key):
        """Remove the profiles of *key* and any strips that are left empty."""
        for kind_key in [k for k in self.profiles if k[1] == key]:
            item = self.profiles.pop(kind_key)[0]
            self.strips[kind_key[0]].removeItem(item)
        used = {kind for kind, _key in self.profiles}
        for kind in set(self.strips) - used:
            strip = self.strips.pop(kind)
            self.layout.removeItem(strip.box)
            if kind == "y":
                self.layout.removeItem(strip.axes[0])
        self._place()
        self._settle()

    def set_log(self, log):
        self.log = log
        for (kind, _key), (item, _positions, _values) in self.profiles.items():
            item.setLogMode(kind == "y" and log, kind != "y" and log)
        for strip in self.strips.values():
            strip.axes[0].setLogMode(log)
        for kind in self.strips:
            self._fit(kind)

    def set_compact(self, compact):
        """Use thinner strips with fewer labels in a compact plot."""
        if compact != self.compact:
            self.compact = compact
            for strip in self.strips.values():
                strip.set_compact(compact)
            self._size()

    def set_depth(self, share):
        """Set the dragged strip depth as a share of the smaller side.

        None restores the automatic depth.
        """
        self.dragged = share
        self._size()
        self._settle()

    def smaller(self):
        return min(self.layout.size().width(), self.layout.size().height())

    def _size(self):
        share, low, high = COMPACT_DEPTH if self.compact else STRIP_DEPTH
        if self.dragged is not None:
            share, low, high = self.dragged, DRAGGED_MIN, LARGE
        side = self.smaller()
        depth = int(np.clip(share * side, low, min(high, MAX_SHARE * side)))
        if depth != self.depth:
            self.depth = depth
            self._place()

    def _place(self):
        if self.depth is None:
            self._size()
            return
        line = self.strips.get("line")
        self.below = line is not None and len(self.strips) == 1
        cells = {"y": (1, 0), "x": (2, 1), "line": (2, 1 if self.below else 0)}
        where = self.layout.items.get(line.box) if line is not None else None
        if where and where != [cells["line"]]:
            self.layout.removeItem(line.box)
        for kind, strip in self.strips.items():
            strip.size_to(self.depth)
            if strip.box not in self.layout.items:
                self.layout.addItem(strip.box, *cells[kind])
                if kind == "y":
                    # The values of the y strip go above the strip.
                    self.layout.addItem(strip.axes[0], 0, 0)
                    self.layout.layout.setAlignment(
                        strip.axes[0], Qt.AlignmentFlag.AlignRight
                    )
        self.mirror()
        self._align()

    def mirror(self):
        """Show the image axes outside the strips instead of the plot axes."""
        for side, kind in (("left", "y"), ("bottom", "x")):
            strip = self.strips.get(kind)
            self.plot.showAxis(side, strip is None)
            if strip is not None:
                strip.mirror()

    def _settle(self):
        """Lay out right away so that Qt never paints a frame with items in
        their old places."""
        items = [self.layout, self.plot, *(s.box for s in self.strips.values())]
        for _ in range(4):
            for item in items:
                settle_layout(item)

    def _align(self):
        view, size = self.plot.vb.geometry(), self.plot.size()
        y, line = self.strips.get("y"), self.strips.get("line")
        ticks = (
            0.0 if y is None else y.image_axis.maximumWidth(),
            0.0 if line is None or self.below else line.axes[0].maximumWidth(),
        )
        for strip in self.strips.values():
            if strip.vertical:
                strip.align(view.top(), size.height() - view.bottom(), ticks)
            else:
                strip.align(view.left(), size.width() - view.right(), ticks)
