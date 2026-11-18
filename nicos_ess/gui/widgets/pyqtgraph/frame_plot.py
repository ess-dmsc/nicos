"""A `FrameView` plots a `Frame` as an item for a shared canvas.

A `Frame` is a labelled N-D array. The plot menu opens from the name in the
title or with a right-click. In the menu the user chooses to draw an image of
two dims, a curve along one dim or the total over time. A click on an axis
label also chooses the dim on that axis. Each dim that is not drawn gets a
range slider under the plot, and the plot sums or averages that dim over the
chosen window of bins. The title line shows the name and some facts about the
data. A box next to the pointer shows the values under it.
"""

from __future__ import annotations

import functools
import time
import weakref
from dataclasses import replace

import numpy as np
import pyqtgraph as pg

from nicos.guisupport.qt import QMenu, QObject, QPointF, Qt, QTimer, pyqtSignal
from nicos_ess.gui.widgets.pyqtgraph import frame_format as fmt
from nicos_ess.gui.widgets.pyqtgraph import theme
from nicos_ess.gui.widgets.pyqtgraph.corrections import SHOWN, Corrections
from nicos_ess.gui.widgets.pyqtgraph.curve import Curve
from nicos_ess.gui.widgets.pyqtgraph.frame_image import FrameImage
from nicos_ess.gui.widgets.pyqtgraph.measure_editor import TOOLS as MEASURE_TOOLS
from nicos_ess.gui.widgets.pyqtgraph.measure_editor import MeasureEditor
from nicos_ess.gui.widgets.pyqtgraph.plot_parts import (
    DataShape,
    HoverBox,
    PlotMenu,
    Title,
    check_action,
    clear_menu,
    radio_entries,
    settle_layout,
    submenu,
)
from nicos_ess.gui.widgets.pyqtgraph.plot_view_box import PlotViewBox
from nicos_ess.gui.widgets.pyqtgraph.profiles import SideProfiles, finite_mean
from nicos_ess.utilities.frame_views import axis, flat_views, view_label, view_of, views
from nicos_ess.utilities.live_frame import curve_frame
from nicos_ess.utilities.series import Series

EMPTY = "No data"
HISTORY = 20_000  # Number of totals a plot keeps without a shared history.
# The line of totals breaks at a pause longer than GAP seconds and three usual steps.
GAP = 10
# A plot below this width or height in px is drawn compact without axis labels.
COMPACT_SIZE = (320, 240)
# These states stop the view from following the data. Each note in the title
# has a hint for the tooltip.
HELD = {
    "zoomed": "The plot is zoomed. Reset zoom in the plot menu follows the data again.",
    "colours fixed": (
        "The colours are fixed. Scale to each image in the Colours menu follows"
        " the data again."
    ),
    "only this plot": "Only this plot is shown. A double-click shows all plots.",
}
PROFILES_TIP = "The mean of every column and row, along the image's edges"


_VIEWS_WITH_AGE = weakref.WeakSet()


@functools.cache
def _age_timer():
    """Return the single timer that updates the age in all plot titles."""

    def tick():
        for view in list(_VIEWS_WITH_AGE):
            try:
                widget = view.item.getViewWidget()
            except RuntimeError:  # Qt has already deleted the canvas.
                _VIEWS_WITH_AGE.discard(view)
                continue
            if widget is not None and widget.isVisible():
                view.update_title()

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(1000)
    return timer


class _Sample(pg.ItemSample):
    """This legend sample ignores clicks.

    The pyqtgraph sample hides its curve when the user clicks it.
    """

    def mouseClickEvent(self, ev):
        ev.ignore()


class FrameView(QObject):
    """A FrameView plots one output.

    Add `item` to a canvas and pass frames to `show_frame`. The ``changed``
    signal asks the owner to save `state()`. *extra_menu(entries, view)* adds
    the owner's menu entries. *history* is a `Series` of totals that the
    owner keeps. Without it the plot keeps its own totals, unless *totals* is
    false and the plot has no "Over time".

    Owners of several curves pass them to `show_frames`. Some keys in
    ``Frame.meta`` style a curve. "label" names the values and "hold" draws
    each value until the next one. "axis" puts a curve on the "left" or
    "right" axis. The texts in "facts" follow the first fact in the title and
    stay when the title is narrow.
    """

    changed = pyqtSignal()
    hide_requested = pyqtSignal()
    solo_requested = pyqtSignal()
    overlays_changed = pyqtSignal()
    measured = pyqtSignal()
    # This carries the tool that the user chose in the plot menu.
    arm_chosen = pyqtSignal(object)

    def __init__(self, name, extra_menu=None, history=None, totals=True):
        super().__init__()
        self.name, self.extra_menu = name, extra_menu
        self.frame = self.received = self.pending = self.view = None
        # Seconds between the last two frames. The owner sets this.
        self.period = 0.0
        # self.windows maps a dim that is not drawn to the (start, stop) of the
        # bins that the plot combines. A dim without a window is combined whole.
        # Shift + wheel moves the window of the dim in self.stepping.
        self.choice, self.windows, self.stepping = (), {}, None
        # Windows of dims that the last frame did not have wait here for data with them.
        self._saved_windows = {}
        self.log = self.frozen = self.full_profiles = self.compact = False
        self.solo = False
        # The owner sets this when the plot is behind the other outputs.
        self.lagging = False
        # The menu entry with this text emits hide_requested.
        self.hide_text = "Hide this plot"
        self.show_history = None  # None shows the totals for single values.
        self.records, self.totals = history is None and totals, totals
        self.history = Series(maxlen=HISTORY) if history is None else history
        self.overlays, self.overlay_frames = [], {}
        self.color_index = {}  # An overlay keeps its colour once it has one.
        self.sides = {}  # Maps curve names to "left", "right" or "hidden".
        self.curve_name = None  # Without a curve name the legend uses the plot name.
        # The style holds the user's choice of "points" and "lines".
        self.show_legend, self.style = None, {}
        # True when the legend fits in a quarter of the plot height.
        self.legend_fits = True
        # The user dragged the profile strips in the grid to this share of the
        # smaller side. None means the depth is automatic.
        self.strip_depth = None
        self.colors = {}  # This holds the saved `ImageLayer.state`.
        self.corrections, self.correction_note = Corrections(), ""
        # This is the shown image before the corrections.
        self.uncorrected = None
        self.measure = MeasureEditor()
        self.measure.placed.connect(self.measured)
        self.measure.scale_changed.connect(self.update_title)
        self.measure.scale_changed.connect(self.changed)
        self.armed = None  # The next drag or click places this tool.
        self.hover, self._pointer = "", None
        self._saved_view = self._quantities = self._shown_dims = None
        self.item = pg.GraphicsLayout()
        # Right-clicks that no item took, as beside an image, open the plot menu too.
        self.item.mouseClickEvent = self._clicked
        self.item.setContentsMargins(2, 0, 2, 0)
        self.item.layout.setSpacing(0)
        self.title_item = Title(menu=True)
        self.title_item.menu_requested.connect(lambda pos: self.plot_menu.open(pos))
        self.item.addItem(self.title_item, row=0, col=0)
        self.hover_box = HoverBox(self.item)
        self.plot = self.image = self.profiles = None
        self._build("curve")
        self.sliders = RangeSliders()
        self.sliders.moved.connect(self.set_window)
        self.item.addItem(self.sliders, row=2, col=0)
        self.axis_menu = QMenu()
        self.item.destroyed.connect(self.axis_menu.deleteLater)
        self.redraw()
        self.item.geometryChanged.connect(self._fit_cell)

    def show_frame(self, frame, received=None):
        """Show *frame*.

        The title shows the age of the data from ``meta["time"]`` or else
        from *received*, which is the time the frame arrived. Without either
        the title shows no age.
        """
        # A slider move redraws the plot, and the total of a big frame takes long.
        self._total = (frame, fmt.total_of(frame))
        if self.records:
            self.history.add(
                frame.meta.get("time") or received or time.time(), self._total[1]
            )
        # A frozen plot keeps its frame so the title still matches the picture.
        if self.frozen:
            self.pending = (frame, received)
            return
        self.frame = frame
        self.received = received
        if self.age() is not None:
            _VIEWS_WITH_AGE.add(self)
            _age_timer()
        choices = self.known_choices()
        if self._saved_view is not None:
            labels = {view_label(c): c for c in choices}
            if self._saved_view in labels:
                self.choice = labels[self._saved_view]
                self._saved_view = None
        if self.choice not in choices:
            # The chosen view comes back with the next frame that has it.
            if self.choice is not None and self._saved_view is None:
                self._saved_view = view_label(self.choice)
            self.choice = choices[0]
        hidden = set(frame.dims) - fmt.shown_dims(self.choice)
        windows = {**self._saved_windows, **self.windows}
        self._saved_windows = {d: w for d, w in windows.items() if d not in frame.dims}
        self.windows = {}
        for dim in hidden & set(windows):
            if window := fit_window(windows[dim], frame.sizes[dim]):
                self.windows[dim] = window
        # This comes after the slices fit the frame, because it may draw the title.
        self._same_quantities(
            (tuple((d, axis(frame, d).unit) for d in frame.dims), frame.unit)
        )
        self.redraw()

    def show_frames(self, frames, received=None):
        """Show the first frame and draw the others as curves over it."""
        first, *others = frames
        self.curve_name = first.name
        self.overlay_frames = {frame.name: frame for frame in others}
        self.overlays = list(self.overlay_frames)
        self.show_frame(first, received)

    def choices(self):
        return views(self.frame) + flat_views(self.frame) if self.frame else []

    def known_choices(self):
        """Return the choices and the images of the choices with swapped axes."""
        choices = self.choices()
        swapped = [c[::-1] for c in choices if len(c) == 2]
        return list(dict.fromkeys(choices + swapped))

    def _set(self, **settings):
        self.__dict__.update(settings)
        self.redraw()
        self.changed.emit()

    def set_choice(self, choice):
        if isinstance(choice, str):
            labels = {view_label(c): c for c in self.known_choices()}
            choice = labels.get(choice, self.choice)
        self._saved_view, self._saved_windows = None, {}
        hidden = set(self.frame.dims) - fmt.shown_dims(choice) if self.frame else set()
        windows = {d: w for d, w in self.windows.items() if d in hidden}
        self._set(choice=choice, windows=windows)

    def set_window(self, dim, window):
        """Combine the bins (start, stop) of *dim*, or all bins if *window* is None."""
        window = fit_window(window, self.frame.sizes[dim])
        if window is None:
            self.windows.pop(dim, None)
        else:
            self.windows[dim] = window
        self.stepping = dim
        self._set()

    def step_window(self, step):
        """Move the window of the last dim that the user moved by *step* bins."""
        dims = [self.stepping, *self.windows]
        dim = next((d for d in dims if d in self.windows), None)
        if dim is None:
            return False
        start, stop = self.windows[dim]
        self.set_window(dim, (start + step, stop + step))
        return True

    def set_log(self, log):
        self._set(log=log)

    def set_show_history(self, on):
        self._set(show_history=on)

    def set_full_profiles(self, on):
        self._set(full_profiles=on)

    def set_frozen(self, frozen):
        self.frozen = frozen
        pending, self.pending = self.pending, None
        if not frozen and pending:
            self.show_frame(*pending)
        else:
            self.redraw()
            self.update_title()

    def set_overlay(self, name, on):
        if name in self.overlays:
            self.overlays.remove(name)
        if on:
            self.overlays.append(name)
        self.overlays_changed.emit()
        self.changed.emit()

    def set_solo(self, solo):
        """Show the plot alone or together with the others.

        A profile strip depth that the user dragged while the plot was alone
        is dropped when the other plots come back.
        """
        if self.profiles is not None and self.solo and not solo:
            self.profiles.set_depth(self.strip_depth)
        self.solo = solo

    def _depth_dragged(self):
        if not self.solo:
            self.strip_depth = self.profiles.dragged
        self.changed.emit()

    def zoomed(self):
        return not all(self.plot.vb.state["autoRange"])

    def follow_data(self):
        self.plot.vb.enableAutoRange()
        self.update_title()

    def age(self):
        """Return the age of the data in seconds, or None if it has no time."""
        meta = {} if self.frame is None else self.frame.meta
        stamp = meta.get("time") or self.received
        return None if stamp is None else time.time() - stamp

    def history_shown(self):
        # A single value without dims can only be drawn over time.
        if self.totals and self.frame is not None and not self.frame.dims:
            return True
        if self.show_history is not None:
            return self.show_history
        return self.totals and self.frame is not None and self.frame.data.size == 1

    def redraw(self):
        empty = self.frame is None or not self.frame.data.size
        self.empty_note.setVisible(empty)
        for side in ("left", "bottom"):
            self.plot.showAxis(side, not empty)
        # Hide the old curves under "No data". The legend and the right axis
        # come back when new curves are drawn.
        data = (self.plot.vb.childGroup, self.right)
        for item in (*data, self.legend, self.plot.getAxis("right")):
            if item is not None and (empty or item in data):
                item.setVisible(not empty)
        if empty:
            self.view = None  # Otherwise the hover box shows old values.
            self.sliders.set_rows([])
            self._follow_pointer()
        if empty or self.frozen:
            self.update_title()
            return
        if self.history_shown():
            self.view = None
            self._draw_curve(self._totals())
        else:
            view = self.view = view_of(self.frame, self.choice, self.windows)
            if view.data.ndim == 1:
                self._draw_curve(view)
            else:
                self._draw_image(view)
        self._show_sliders()
        self._follow_pointer()
        shown = self.view.dims if self.view is not None else "history"
        # A zoom on other dims means nothing for the new view.
        if self._shown_dims not in (None, shown):
            self.plot.vb.enableAutoRange()
        self._shown_dims = shown
        self.update_title()

    def _show_sliders(self):
        rows = []
        for dim in self.frame.dims if self.view is not None else ():
            if dim not in fmt.shown_dims(self.choice):
                size = self.frame.sizes[dim]
                start, stop = self.windows.get(dim, (0, size))
                text = fmt.format_position(axis(self.frame, dim), start, stop)
                rows.append(Row(dim, size, (start, stop), text))
        self.sliders.set_rows(rows)

    def _same_quantities(self, shown):
        """Follow the data again when the axes or units of the data change.

        That happens with another source but not when the user picks another
        view of the same data.
        """
        held = self.zoomed() or (self.layer is not None and not self.layer.follow)
        if held and self._quantities not in (None, shown):
            self.follow_data()
            if self.layer is not None:
                self.layer.set_mode("always")
        elif self.layer is None and self._quantities not in (None, shown):
            # The restored colour levels were kept for other data.
            self.colors = {**self.colors, "mode": "always"}
        if self._quantities not in (None, shown):
            # The references, the length scale and the log scale were chosen
            # for the other data.
            self.corrections.forget()
            self.measure.set_length_scale(None)
            self.log = False
        self._quantities = shown

    def _build(self, kind, time_axis=False):
        bottom = theme.TimeAxisItem if time_axis else theme.CompactAxisItem
        if self.plot is not None and (kind == "image") == (self.image is not None):
            # Replace only the axis so the items that owners added stay.
            if type(self.plot.getAxis("bottom")) is not bottom:
                self.plot.setAxisItems({"bottom": bottom("bottom")})
                self.plot.updateGrid()
                self._hook_axis("bottom")
            return
        if self.image is not None:
            self.measure.detach()
        if self.plot is not None:
            self.item.removeItem(self.body)
        # The body holds the plot and the profile strips along the image.
        self.body = pg.GraphicsLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.layout.setSpacing(0)
        self.item.addItem(self.body, row=1, col=0)
        axes = {"left": theme.CompactAxisItem("left"), "bottom": bottom("bottom")}
        self.plot = pg.PlotItem(viewBox=PlotViewBox(self), axisItems=axes)
        self.plot.hideButtons()
        self.plot.showGrid(x=True, y=True, alpha=0.12)
        vb = self.plot.vb
        for side in ("left", "bottom"):
            self._hook_axis(side)
        vb.surface.setVisible(self.armed is not None)
        self.body.addItem(self.plot, row=1, col=1)
        self.plot.layout.setContentsMargins(0, 2, 2, 0)
        vb.sigRangeChangedManually.connect(self.update_title)
        vb.sigRangeChanged.connect(self._follow_pointer)
        self.empty_note = pg.TextItem(EMPTY, color=theme.MUTED, anchor=(0.5, 0.5))
        self.empty_note.setParentItem(vb)
        self.empty_note.setVisible(self.frame is None)
        vb.sigResized.connect(lambda: self.empty_note.setPos(vb.rect().center()))
        self.plot_menu = PlotMenu(self.plot, self._add_entries, self.follow_data)
        self.curve = self.layer = self.legend = self.profiles = self.shape = None
        self.image = self.right = self.pointer_line = None
        self.overlay_curves, self.overlay_views = {}, {}
        # not_shown counts the values that the log scale cannot show.
        self.hidden_curves, self.not_shown = [], 0
        if kind == "image":
            self.image = FrameImage(self.plot)
            self.layer = self.image.layer
            self.layer.restore(self.colors)
            self.layer.changed.connect(self._colors_changed)
            self.profiles = SideProfiles(self.body, self.plot, self.image)
            self.profiles.dragged = self.strip_depth
            self.profiles.depth_dragged.connect(self._depth_dragged)
            self.shape = DataShape(self.plot, self.body)
            vb.setDefaultPadding(0.0)
            self.plot.showGrid(False, False)
            self.measure.attach(self.plot, self.image, self.profiles)
        else:
            self.curve = Curve(self.plot, theme.curve_color(0))
            self.pointer_line = pg.InfiniteLine(angle=90, pen=theme.POINTER_PEN)
            self.pointer_line.hide()
            self.plot.addItem(self.pointer_line, ignoreBounds=True)
        self._apply_compact()

    def _hook_axis(self, side):
        """Open the menu of the dims for an axis on a left click on its label.

        A compact plot hides the labels, so there the whole axis takes the click.
        """
        item = self.plot.getAxis(side)
        clicked = item.mouseClickEvent

        def click(ev):
            label = item.label
            on_label = label.sceneBoundingRect().contains(ev.scenePos())
            left = ev.button() == Qt.MouseButton.LeftButton and not ev.double()
            if left and (on_label or not label.isVisible()) and self.axis_choices(side):
                ev.accept()
                self.open_axis_menu(side, ev.screenPos().toPoint())
            else:
                clicked(ev)

        item.mouseClickEvent = click

    def axis_choices(self, side):
        """Return the views that change only the dim on *side*, with that dim.

        Choosing the dim of the other axis swaps the axes.
        """
        choice = self.choice
        # An image has its first dim on the left axis.
        sides = ("bottom",) if len(choice) == 1 else ("left", "bottom")
        if self.view is None or self.history_shown() or side not in sides:
            return {}
        k, known, found = sides.index(side), self.known_choices(), {}
        for part in dict.fromkeys(p for c in known if len(c) == len(choice) for p in c):
            new = list(choice)
            if part in choice:
                new[choice.index(part)] = choice[k]
            new[k] = part
            if tuple(new) in known:
                found[tuple(new)] = view_label((part,))
        return found if len(found) > 1 else {}

    def open_axis_menu(self, side, pos):
        clear_menu(self.axis_menu)
        found = self.axis_choices(side)
        radio_entries(self.axis_menu, found, self.choice, self.set_choice)
        self.axis_menu.popup(pos)

    def _clicked(self, ev):
        if ev.button() == Qt.MouseButton.RightButton:
            ev.accept()
            self.plot_menu.open(ev.screenPos().toPoint())

    def _fit_cell(self):
        self._fit_legend()
        size = self.item.size()
        compact = size.width() < COMPACT_SIZE[0] or size.height() < COMPACT_SIZE[1]
        if compact != self.compact:
            self.compact = compact
            self._apply_compact()

    def _apply_compact(self):
        """A compact plot has no axis labels, no legend and a narrow colour bar.

        The title still shows the unit.
        """
        for side in ("left", "right"):
            item = self.plot.getAxis(side)
            item.showLabel(not self.compact and bool(item.labelText))
        self._show_legend()
        if self.layer is not None:
            self.layer.colorbar.set_compact(self.compact)
        if self.profiles is not None:
            self.profiles.set_compact(self.compact)
            self.profiles.mirror()
            settle_layout(self.item)

    def _colors_changed(self):
        self.colors = self.layer.state()
        self.changed.emit()
        self.update_title()

    def _labels(self, x, y=None):
        self.plot.getAxis("bottom").integers = fmt.is_pixels(x)
        self.plot.getAxis("left").integers = y is not None and fmt.is_pixels(y)
        self.plot.setLabel("bottom", *fmt.axis_label(x))
        if y is None:
            # The label comes from meta "label", otherwise from the name of a
            # single curve, otherwise from the unit.
            one = None if self.overlay_curves else self.curve_name
            label = self.frame.meta.get("label") or one
            self.plot.setLabel(
                "left", label or self.frame.unit, label and self.frame.unit
            )
        else:
            self.plot.setLabel("left", *fmt.axis_label(y))
        self._apply_compact()

    def _set_legend(self, entries):
        """Show the legend in rows under the plot so it never covers a curve."""
        if self.legend is None and entries:
            size = theme.css_size(theme.TICK_SCALE)
            self.legend = pg.LegendItem(labelTextSize=size, sampleType=_Sample)
            self.legend.setMinimumWidth(1)  # Otherwise a long name widens the plot.
            self.plot.layout.addItem(self.legend, 4, 1)
        shown = [(s.item, label.text) for s, label in getattr(self.legend, "items", ())]
        if self.legend is not None and shown != entries:
            self.legend.clear()
            for item, label in entries:
                self.legend.addItem(item, label)
            self._fit_legend()

    def _fit_legend(self):
        if self.legend is not None and self.legend.items:
            items = self.legend.items
            entry = max(s.width() + label.minimumWidth() for s, label in items)
            columns = max(1, min(len(items), int(self.item.width() // (entry + 20))))
            self.legend.setColumnCount(columns)
            rows, row = -(-len(items) // columns), items[0][1].item.boundingRect()
            self.legend_fits = rows * row.height() <= self.item.height() / 4
            self._show_legend()

    def legend_on(self):
        """Return whether the legend is shown.

        Unless the user chose, the legend is shown only where it fits. The
        hover box names the curves anyway.
        """
        return self.legend_fits if self.show_legend is None else self.show_legend

    def _show_legend(self):
        if self.legend is not None:
            shown = self.legend_on() and not self.compact and bool(self.overlay_curves)
            self.legend.setVisible(shown)
            self.legend.setMaximumHeight(1e6 if shown else 0)

    def _right_view(self):
        """Return the view box for the right axis.

        It shares x with the plot and has its own y range, which zooms and
        pans together with the left axis. The mouse always acts on the plot.
        """
        if self.right is None:
            vb, right = self.plot.vb, pg.ViewBox(enableMenu=False)
            self.right, self._left_y = right, vb.viewRange()[1]
            right.setParentItem(self.plot)
            right.setZValue(vb.zValue() - 1)
            right.setMouseEnabled(False, False)
            right.setXLink(vb)
            axis = theme.CompactAxisItem("right")
            self.plot.setAxisItems({"right": axis})
            # The plot only passes the log mode to its axes when it changes.
            axis.setLogMode(False, self.log)
            axis.linkToView(right)
            # The mouse on the right axis acts on the left view box.
            axis.linkedView = lambda: vb
            vb.sigYRangeChanged.connect(self._move_right)
            vb.sigResized.connect(lambda: right.setGeometry(vb.geometry()))
            right.setGeometry(vb.geometry())
        return self.right

    def _move_right(self, vb, new):
        (low, high), self._left_y = self._left_y, list(new)
        # Reset zoom and a new log scale also turn on the auto range.
        if vb.state["autoRange"][1]:
            self.right.enableAutoRange(y=True)
        elif high > low:
            bottom, top = self.right.viewRange()[1]
            scale = (top - bottom) / (high - low)
            self.right.setYRange(
                bottom + (new[0] - low) * scale,
                top + (new[1] - high) * scale,
                padding=0,
            )

    def _draw_curve(self, view):
        x = axis(view, view.dims[0])
        self._build("curve", x.is_time)
        # This comes first because it empties a curve with no value above 0.
        self.curve.set_log(self.log)
        self.plot.setLogMode(y=self.log)
        self.not_shown = int(np.sum(view.data <= 0)) if self.log else 0
        self.curve.set_floor(view.counts)
        self._set_curve(self.curve, view)
        self._draw_overlays(x)
        # The legend is only shown with overlays, so draw them first.
        self._labels(x)
        whole = view.counts and not np.any(np.mod(view.data, 1))
        self.plot.getAxis("left").integers = "counts" if whole else False

    def _set_curve(self, curve, view):
        style = {"lines": True, "points": False, **self.style}
        curve.set_style(lines=style["lines"], symbols=style["points"])
        x = axis(view, view.dims[0]).values
        curve.set_data(x, view.data, view.errors, hold=view.meta.get("hold", False))

    def _draw_overlays(self, x):
        """Draw the chosen other outputs that have the same dim and x unit.

        Curves in the unit of the plot go on the left axis and curves in a
        second unit go on the right axis, unless ``meta["axis"]`` says
        otherwise. Curves in any further unit are not drawn.
        """
        own, others, self.overlay_views = self.frame.unit, {}, {}
        for name in self.overlays if self.view is not None else ():
            frame = self.overlay_frames.get(name)
            if frame is None or (x.dim not in frame.dims and len(frame.dims) != 1):
                continue
            dim = x.dim if x.dim in frame.dims else frame.dims[0]
            other = view_of(frame, (dim,))
            if fmt.same_unit(axis(other, dim).unit, x.unit):
                others[name] = other
        chosen = [o.unit for o in others.values() if o.meta.get("axis") == "right"]
        # Each axis has one unit.
        units = {"left": own, "right": next(iter(chosen), None)}
        drawn, self.hidden_curves = {}, []
        self.sides = {self.curve_name or self.name: "left"}
        for name, other in others.items():
            same = fmt.same_unit(other.unit, own)
            side = other.meta.get("axis") or ("left" if same else "right")
            if units[side] is None:
                units[side] = other.unit
            if fmt.same_unit(other.unit, units[side]):
                drawn[name] = (other, side == "right")
            else:
                self.hidden_curves.append(name)
            self.sides[name] = side if name in drawn else "hidden"
        for name in set(self.overlay_curves) - set(drawn):
            self.overlay_curves.pop(name).remove()
        entries = [(self.curve.line, self.curve_name or self.name)] * bool(drawn)
        for name, (other, right) in drawn.items():
            plot = self._right_view() if right else self.plot
            curve = self.overlay_curves.get(name)
            if curve is None:
                i = self.color_index.setdefault(name, len(self.color_index) + 1)
                curve = self.overlay_curves[name] = Curve(plot, theme.curve_color(i))
            elif curve.plot is not plot:
                curve.move_to(plot)
            curve.set_log(self.log)
            self._set_curve(curve, other)
            self.overlay_views[name] = other
            entries.append((curve.line, name + " (right axis)" * right))
        self._set_legend(entries)
        on_right = any(right for *_p, right in drawn.values())
        self.plot.showAxis("right", on_right)
        if on_right:
            self.plot.setLabel("right", units["right"])

    def _totals(self):
        """Return the totals over time as a frame.

        A NaN after each pause breaks the line there.
        """
        t, v = self.history.arrays()
        if len(t) > 2:
            steps = np.diff(t)
            at = np.flatnonzero(steps > max(GAP, 3 * np.median(steps))) + 1
            t, v = np.insert(t, at, t[at - 1]), np.insert(v, at, np.nan)
        return curve_frame("time", self.frame.unit, t, v, "datetime64[s]")

    def _draw_image(self, view):
        y, x = (axis(view, dim) for dim in view.dims)
        self._build("image", x.is_time)
        # Pixel rows have no unit and count from the top like in daqlite and
        # the camera software.
        self.plot.vb.invertY(not y.unit)
        self.layer.set_log(self.log)
        self.profiles.set_log(self.log)
        x_edges, y_edges = fmt.edges_of(x), fmt.edges_of(y)
        self.uncorrected = view
        # The hover box and the title then show the corrected values.
        self.view, self.correction_note = self.corrections.apply(
            view, (x_edges, y_edges)
        )
        values = np.asarray(self.view.data, dtype=float)
        self.image.set_image(values, x, y, x_edges, y_edges, view.counts)
        self.layer.colorbar.set_label(self.view.unit)
        self.profiles.unit = self.view.unit
        self.not_shown = int(np.sum(values <= 0)) if self.log else 0
        if self.full_profiles:
            self.profiles.set("x", "full", x_edges, finite_mean(values, 0))
            self.profiles.set("y", "full", y_edges, finite_mean(values, 1))
        else:
            self.profiles.drop("full")
        square = fmt.keeps_proportions(x, y)
        self.plot.setAspectLocked(square)
        width, height = (abs(e[-1] - e[0]) or 1.0 for e in (x_edges, y_edges))
        self.shape.set_aspect(width / height if square else None)
        self._labels(x, y)

    def title_parts(self):
        """Return the title parts as (text, colour, kept) in the order shown.

        On a narrow title the last parts that are not kept are left out, see
        `Title`. Parts that come and go with the data are at the end so the
        other parts do not move.
        """
        frame, muted, attention = self.frame, theme.MUTED, theme.ATTENTION
        if frame is None:
            return []  # The plot itself says "No data".
        parts = []
        if self.layer is not None and self.correction_note:
            parts.append((self.correction_note, theme.ALERT, True))
        if self.history_shown():
            total = "Σ" if frame.counts else "mean"
            last = fmt.readable(self.history.last_value)
            first = f"{total} {last} {frame.unit}".rstrip()
            rest = [f"{len(self.history)} points over time"]
        else:
            if self.image and self.view and self.view is not self.uncorrected:
                # The title describes the corrected values.
                frame = replace(frame, unit=self.view.unit, counts=self.view.counts)
                total = fmt.total_of(self.view)
            elif self._total[0] is frame:
                total = self._total[1]
            else:
                total = fmt.total_of(frame)
            first, *rest = fmt.facts(frame, total) or [None]
        # The first fact has the unit, which a compact plot shows nowhere else.
        if first:
            parts.append((first, muted, True))
        parts += [(text, muted, True) for text in frame.meta.get("facts", ())]
        if self.layer is not None:
            parts += [(text, attention, True) for text in self.corrections.applied()]
        parts += [("frozen", attention, True)] * self.frozen
        # This is muted because a colour would look like the colour of a curve.
        if hidden := self.hidden_curves:
            parts.append((f"{len(hidden)} hidden", muted, True))
            parts.append((f"{', '.join(hidden)} in another unit", muted, False))
        if self.not_shown:
            values = "value" + "s" * (self.not_shown != 1)
            parts.append((f"{self.not_shown} {values} ≤ 0 not shown", muted, True))
        parts += [(note, attention, True) for note in self.held()]
        parts += [(text, muted, False) for text in rest]
        if self.measure.length_scale is not None and self.image is not None:
            factor, unit = self.measure.length_scale
            own = self.image.axis_unit("x") or "px"
            parts.append((f"1 {own} = {fmt.readable(factor)} {unit}", attention, False))
        if saturated := frame.meta.get("saturated"):
            parts.append((f"{saturated} px saturated", theme.ALERT, True))
        if age := fmt.age_text(self.age(), self.period):
            parts.append((age, theme.ALERT if self.lagging else muted, True))
        return parts

    def held(self):
        """Return the notes of the `HELD` states that apply now."""
        fixed = self.layer is not None and not self.layer.follow
        states = (self.zoomed(), fixed, self.solo)
        return [note for note, on in zip(HELD, states, strict=True) if on]

    def update_title(self):
        hints = [HELD[note] for note in self.held()]
        title = "" if self.frame is None or self.history_shown() else self.frame.title
        hints += [title] * (title not in ("", self.name))
        self.title_item.set_parts(self.name, self.title_parts(), hints)

    def take_reference(self, which):
        """Keep the uncorrected image as the "background" or "flat field"."""
        # The shown view, because a frozen plot keeps an image of older choices.
        # The shown view holds the corrected values, so the reference comes
        # from the same image before the corrections.
        view = self.view
        if self.image is not None and view is not None and view.data.ndim == 2:
            view = self.uncorrected
            y, x = (fmt.edges_of(axis(view, d)) for d in view.dims)
            self.corrections.take(which, view.data, (x, y), view.meta.get("exposure"))
            self._set()

    def set_correction(self, attr, value):
        """Set the correction setting *attr*, or forget all if *attr* is None."""
        if attr is None:
            self.corrections.forget()
        else:
            setattr(self.corrections, attr, value)
        self._set()

    def _add_correction_entries(self, menu):
        refs = self.corrections.references
        for which in refs:
            take = functools.partial(self.take_reference, which)
            menu.addAction(f"Take {which} from this image", take)
        menu.addSeparator()

        # Return the tooltip of an entry whose reference is missing.
        def needs(which):
            missing = which != "image" and refs[which] is None
            return f"Take a {which} first" if missing else ""

        for text, attr, which in (
            ("Subtract background", "subtract", "background"),
            ("Divide by flat field", "divide", "flat field"),
        ):
            on, tip = getattr(self.corrections, attr), needs(which)
            set_on = functools.partial(self.set_correction, attr)
            check_action(menu, text, on, set_on, tip).setEnabled(not tip)
        menu.addSeparator()
        shown = {which: f"Show the {which}" for which in SHOWN}
        set_shown = functools.partial(self.set_correction, "shown")
        radio_entries(menu, shown, self.corrections.shown, set_shown)
        for action, which in zip(menu.actions()[-len(SHOWN) :], SHOWN, strict=True):
            action.setToolTip(needs(which) or action.text())
            action.setEnabled(not needs(which))
        forget = functools.partial(self.set_correction, None, None)
        taken = any(r is not None for r in refs.values())
        menu.addAction("Forget the references", forget).setEnabled(taken)

    def arm(self, kind):
        """Arm the measurement tool *kind*; None pans again."""
        self.armed = kind if kind in MEASURE_TOOLS else None
        self.plot.vb.surface.setVisible(self.armed is not None)

    def choose_arm(self, kind):
        """Arm *kind* from a menu and tell the tool bar of the owner."""
        self.arm(kind)
        self.arm_chosen.emit(self.armed)

    def _follow_pointer(self, *_args):
        if self.hover and self._pointer is not None:
            self.hover_at(self._pointer)

    def hover_at(self, scene_pos):
        """Show the values under *scene_pos* and return whether it is on data."""
        self._pointer = scene_pos
        vb = self.plot.vb
        inside = vb.sceneBoundingRect().contains(scene_pos)
        where, rows = "", []
        # The values are not shown over a measurement label.
        if inside and not self.measure.label_at(scene_pos):
            where, rows = self._pointer_rows(vb.mapSceneToView(scene_pos), scene_pos)
        elif self.profiles is not None:
            where, rows = self.profiles.pointer_rows(scene_pos)
        values = " · ".join(f"{name} {value}".lstrip() for _c, name, value, _d in rows)
        self.hover = f"{where}: {values}" if rows else ""
        at, area = self.item.mapFromScene(scene_pos), vb.sceneBoundingRect()
        self.hover_box.show_rows(where, rows, at, self.item.mapRectFromScene(area))
        if self.pointer_line is not None:
            self.pointer_line.setVisible(inside and bool(rows))
            self.pointer_line.setPos(vb.mapSceneToView(scene_pos).x())
        return inside and self.view is not None

    def _pointer_rows(self, point, scene_pos):
        """Return the position text and one row per curve or for the image.

        A row is (colour, name, value, distance in px).
        """
        if self.view is not None and self.view.data.ndim == 2:
            found = fmt.pointer_at(self.view, point.x(), point.y())
            if found is None:
                return "", []
            return found[0], [(None, "", fmt.value_text(self.view, found[1]), 0.0)]
        if self.view is None:
            shown = self.frame is not None and self.history_shown() and self.history
            curves = [(self.curve, "", self._totals())] if shown else []
        else:  # The curves only need names when there are several.
            name = (self.curve_name or self.name) * bool(self.overlay_views)
            curves = [(self.curve, name, self.view)]
            curves += [
                (self.overlay_curves[n], n, v) for n, v in self.overlay_views.items()
            ]
        where, rows = "", []
        for curve, name, view in curves:
            if (found := fmt.pointer_at(view, point.x())) is None:
                continue
            where = where or found[0]
            value = float(view.data[found[1]])
            y = np.log10(value) if self.log and value > 0 else value
            at = curve.line.mapToScene(QPointF(point.x(), y))
            distance = abs(at.y() - scene_pos.y()) if np.isfinite(y) else np.inf
            rows.append((curve.color, name, fmt.value_text(view, found[1]), distance))
        return where, rows

    def _add_entries(self, entries):
        """Add the entries of this plot to *entries*, see `plot_parts.fill_menu`."""
        entries["Log scale"] = ("Log scale", self.log, self.set_log)
        entries["Freeze"] = ("Freeze", self.frozen, self.set_frozen)
        if self.frame is not None:
            entries["Show"] = self._add_show
        # The image layer stays after an empty frame, which shows no image.
        image_shown = self.layer is not None and self.view is not None
        if image_shown:
            entries["Colours"] = submenu("Colours", self.layer.add_menu_entries)
            entries["Corrections"] = submenu(
                "Corrections", self._add_correction_entries
            )
            on, set_on = self.full_profiles, self.set_full_profiles
            entries["Profiles"] = ("Whole-image profiles", on, set_on, PROFILES_TIP)
            entries["Measure"] = lambda m: self.measure.menu_entries(
                m, self.choose_arm, self.armed
            )
        # Only an owner with other plots connects this signal.
        if self.receivers(self.solo_requested):
            only = ("Only this plot (double-click)", self.solo, self.solo_requested)
            entries["Only this plot"] = only
        if self.receivers(self.hide_requested):
            entries["Hide"] = lambda m: m.addAction(self.hide_text, self.hide_requested)
        if self.extra_menu is not None:
            self.extra_menu(entries, self)
        # The owner can add its own "Curves" entries.
        if self.overlay_curves or "Curves" in entries:
            more = entries.get("Curves")
            entries["Curves"] = submenu("Curves", lambda m: self._add_curves(m, more))

    def _add_curves(self, menu, more):
        if self.overlay_curves:
            legend = lambda on: self._set(show_legend=on)  # noqa: E731
            check_action(menu, "Legend", self.legend_on(), legend)
            shown = {"points": self.curve.symbols, "lines": self.curve.lines}
            for key, on in shown.items():  # These styles apply to all curves.
                style = lambda on, k=key: self._set(style=self.style | {k: on})  # noqa: E731
                check_action(menu, key.title(), on, style)
        if more is not None:
            menu.addSeparator()
            more(menu)

    def _add_show(self, menu):
        choices = self.choices() if len(self.choices()) > 1 else []
        # A single value without dims is always drawn over time.
        over_time = self.totals and bool(self.frame.dims)
        if choices or over_time:
            show = menu.addMenu("Show")
            texts = {c: view_label(c) for c in choices}
            # A view with swapped axes checks the entry of the same dims.
            on = next((c for c in choices if set(c) == set(self.choice)), None)
            radio_entries(show, texts, on, self.set_choice)
            if over_time:
                show.addSeparator()  # Qt hides a separator at the top.
                on = self.history_shown()
                check_action(show, "Over time", on, self.set_show_history)

    def state(self):
        return dict(
            view=self._saved_view or (view_label(self.choice) if self.choice else ""),
            log=self.log,
            legend=self.show_legend,
            style=dict(self.style),
            history=self.show_history,
            overlays=list(self.overlays),
            windows={
                d: list(w) for d, w in {**self._saved_windows, **self.windows}.items()
            },
            colors=self.colors,
            length_scale=self.measure.length_scale,
            profiles=self.full_profiles,
            strip_depth=self.strip_depth,
            quantities=self._quantities,
        )

    def restore(self, state):
        """Apply saved settings. The saved view is chosen with the next frame.

        Settings of the wrong type, as in a damaged file, are left out.
        """

        def get(key, kind, default=None):
            value = state.get(key)
            return value if isinstance(value, kind) else default

        self.log = get("log", bool, False)
        self.show_legend = get("legend", bool)
        self.style = dict(get("style", dict, {}))
        self.show_history = get("history", bool)
        self.overlays = [n for n in get("overlays", list, []) if isinstance(n, str)]
        self.colors = dict(get("colors", dict, {}))
        depth = get("strip_depth", (int, float), 0)
        self.strip_depth = depth if 0 < depth < np.inf else None
        self.full_profiles = get("profiles", bool, False)
        scale = get("length_scale", (list, tuple), ())
        valid = len(scale) == 2 and isinstance(scale[0], (int, float))
        self.measure.length_scale = tuple(scale) if valid else None
        windows = get("windows", dict, {})
        self.windows = {
            d: tuple(w)
            for d, w in windows.items()
            if isinstance(w, list) and len(w) == 2 and all(type(i) is int for i in w)
            if 0 <= w[0] < w[1]
        }
        self._saved_windows = {}
        self.stepping = next(iter(self.windows), None)
        self._saved_view = get("view", str)
        try:
            dims, unit = get("quantities", (list, tuple), ())
            # JSON turns the tuples into lists.
            self._quantities = (tuple(tuple(d) for d in dims), unit)
        except (TypeError, ValueError):
            pass


class FrameCanvas(pg.GraphicsLayoutWidget):
    """A canvas without margins for one `FrameView`."""

    def __init__(self, view):
        super().__init__()
        self.view = view
        # A pyqtgraph axis with a grid takes the bounds of its view box, but it
        # does not tell the scene when the view box resizes. The BSP index of
        # the scene then keeps a deleted axis, and the next paint crashes.
        scene = self.scene()
        scene.setItemIndexMethod(scene.ItemIndexMethod.NoIndex)
        self.ci.setContentsMargins(0, 0, 0, 0)
        self.ci.addItem(view.item)
        scene.sigMouseMoved.connect(view.hover_at)
        scene.sigItemRemoved.connect(self._end_drag_of)

    def _end_drag_of(self, item):
        # pyqtgraph sends the rest of a drag to the dragged item even after
        # the item left the scene and was deleted.
        dragged = self.scene().dragItem
        if dragged is not None and (dragged is item or item.isAncestorOf(dragged)):
            self.scene().dragItem = None

    def leaveEvent(self, event):
        self.view.hover_at(QPointF(-1e9, -1e9))
        super().leaveEvent(event)


class Solo:
    """Plots side by side in a panel.

    *canvases* is the collection that the owner keeps, for example a list or
    the values of a dict. The owner calls `add` after it put a canvas in it
    and `remove` after it took one out. A double-click shows one plot alone
    and another double-click shows all of them again. *changed* is called
    after each change.
    """

    def __init__(self, canvases, changed=None):
        self.canvases, self.changed = canvases, changed
        for canvas in canvases:
            self.add(canvas)

    def add(self, canvas):
        """Show all plots together with the new *canvas*."""
        canvas.view.solo_requested.connect(lambda: self.toggle(canvas))
        if any(c.view.solo for c in self.canvases):
            self.show(None)

    def remove(self, canvas):
        if canvas.view.solo:
            self.show(None)

    def toggle(self, canvas):
        solo = any(c.view.solo for c in self.canvases) or len(self.canvases) < 2
        self.show(None if solo else canvas)

    def show(self, alone):
        """Show only *alone*, or all plots if *alone* is None."""
        for other in self.canvases:
            other.view.set_solo(other is alone)
            other.setVisible(alone is None or other is alone)
            other.view.update_title()
        if self.changed:
            self.changed()
