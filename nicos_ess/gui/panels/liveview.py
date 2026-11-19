"""The live view panel shows all live data outputs as a grid of plots.

Several live views (``index`` 1, 2, ...) share one `LiveHub` per connection.
New outputs go to the view with the lowest index; the plot menu moves an
output or shows it in several views. A timer redraws plots of changed
outputs while the panel is visible. The tool bar chooses pan/zoom or a
measurement tool (Esc: pan/zoom).
"""

from __future__ import annotations

import collections
import json
import math
import time
from functools import partial

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QActionGroup,
    QCursor,
    QKeySequence,
    QLabel,
    QMenu,
    QShortcut,
    QSplitter,
    Qt,
    QTimer,
    QToolBar,
    QVBoxLayout,
)
from nicos_ess.gui.live_hub import hub_for
from nicos_ess.gui.widgets.pyqtgraph.frame_plot import FrameCanvas, FrameView, Solo
from nicos_ess.gui.widgets.pyqtgraph.measure_editor import KINDS
from nicos_ess.gui.widgets.pyqtgraph.plot_parts import check_action, submenu

REDRAW_MS = 100
# Drawing stops after this many seconds per tick so that the GUI still
# handles user input.
DRAW_BUDGET = 0.05
CELL_ASPECT = 1.4  # plots should be about this much wider than high
MAX_COLUMNS = 8
# dragging a splitter cannot make a plot smaller than this in pixels
MIN_CELL = (160, 120)
# An output is out of date when it is more than LAG seconds or three of its
# periods behind the newest output.
LAG = 10
EQUAL = 10_000  # QSplitter scales the sizes to fit, so equal values give equal sizes
TOOL_BAR_STYLE = (
    "QToolBar { spacing: 2px; padding: 2px 4px; }"
    " QToolBar > QToolButton { padding: 1px 8px; }"
)


def grid_columns(count, width, height, aspect=CELL_ASPECT):
    """Return the number of columns for *count* plots.

    The cells should be close to *aspect* and few cells should stay empty.
    """
    if count <= 1 or width <= 0 or height <= 0:
        return 1

    def cost(cols):
        rows = math.ceil(count / cols)
        shape = abs(math.log((width / cols) / (height / rows) / aspect))
        return shape + (rows * cols - count) / count

    return min(range(1, min(count, MAX_COLUMNS) + 1), key=cost)


def splitter(orientation, widgets):
    split = QSplitter(orientation)
    split.setHandleWidth(4)
    split.setChildrenCollapsible(False)
    split.setOpaqueResize(False)  # redrawing all plots while dragging lags
    for widget in widgets:
        split.addWidget(widget)
        widget.setMinimumSize(*MIN_CELL)
        widget.show()
    split.setSizes([EQUAL] * split.count())
    return split


class LiveViewPanel(Panel):
    """The panel shows a live view of the outputs placed in it.

    Options: ``index`` (default 1) and ``title`` (default "Live <index>").
    """

    panelName = "Live view"

    def __init__(self, parent, client, options):
        self.index = int(options.get("index", 1))
        self.title = options.get("title") or f"Live {self.index}"
        if self.index != 1:  # The other views need their own settings.
            self.panelName = f"Live view {self.index}"
        # Panel.__init__ calls loadSettings, which fills self._saved.
        self._saved = {}
        Panel.__init__(self, parent, client, options)
        for name in layout.keys() - self.preset.keys():
            self.log.warning("layout of %s needs (x, y, w, h)", name)
        self.hub = hub_for(client, self.log)
        self.views, self.canvases, self.dirty = {}, {}, set()
        # This remembers when each output was last drawn.
        self.drawn = collections.defaultdict(float)
        self.solo = Solo(self.canvases.values(), changed=self.relayout)
        self._key = None
        # splitter sizes that the user set for each arrangement "names|columns",
        # but only the sizes of the shown arrangement are saved
        self.split_states = dict(self._saved.get("splits", {}))
        # the user chose this order of the plots
        self.order = list(self._saved.get("order", []))
        self._shown, self._cols = [], 0
        self.tool = None  # measurement tool, None for pan/zoom
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.tool_bar = self._tool_bar()
        layout.addWidget(self.tool_bar)
        self.grid = QLabel()
        layout.addWidget(self.grid)
        for interval, slot in ((REDRAW_MS, self.draw_dirty), (1000, self.update_ages)):
            timer = QTimer(self)
            timer.timeout.connect(slot)
            timer.start(interval)
        self.hub.arrived.connect(self.on_arrived)
        self.hub.placed.connect(self.sync_views)
        self.hub.register(self)
        self.hub.placed.emit()  # This updates the menus of the other views.

    def _tool_bar(self):
        bar = QToolBar()
        bar.setStyleSheet(TOOL_BAR_STYLE)
        self.tool_actions = {}
        group = QActionGroup(self)

        def add_tool(kind, text, tip=""):
            action = bar.addAction(text)
            action.setCheckable(True)
            action.setToolTip(tip)
            action.triggered.connect(lambda _c=False: self.set_tool(kind))
            group.addAction(action)
            self.tool_actions[kind] = action
            return action

        add_tool("pan", "Pan/zoom", "Drag to pan, wheel to zoom (Esc)")
        # The Measure menu of the plots has the same tools.
        for kind, measure in KINDS.items():
            add_tool(kind, measure.tool, measure.tip)
        self.tool_actions["pan"].setChecked(True)
        clear = bar.addAction("Clear")
        clear.setToolTip("Remove all measurements in this view")
        clear.triggered.connect(self.clear_measures)
        # Esc also restores the command line, so the shortcut only works while
        # the focus is in this panel.
        self.esc_key = QShortcut(QKeySequence("Esc"), self)
        self.esc_key.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.esc_key.activated.connect(lambda: self.set_tool("pan"))
        return bar

    def set_tool(self, kind):
        """Choose the mouse tool: ``pan`` (or None) or a measurement.

        The tool bar also shows a tool that was chosen in a plot menu.
        """
        kind = kind or "pan"
        self.tool = None if kind == "pan" else kind
        self.tool_actions[kind].setChecked(True)
        for view in self.views.values():
            view.arm(self.tool)

    def clear_measures(self):
        for view in self.views.values():
            view.measure.clear()

    def mine(self):
        """Return the names of the outputs placed in this view."""
        return [n for n in self.hub.names() if self.index in self.hub.where(n)]

    def sync_views(self):
        """Make plots for the outputs placed here and drop the others.

        Making a plot takes long, so after DRAW_BUDGET the next turn of the
        event loop makes the rest.
        """
        mine = set(self.mine())
        for name in set(self.views) - mine:
            self._drop_view(name)
        start = time.monotonic()
        for name in sorted(mine - set(self.views)):
            self._make_view(name)
            if time.monotonic() - start > DRAW_BUDGET:
                QTimer.singleShot(0, self.sync_views)
                break
        self.relayout()

    def on_arrived(self, names):
        for name in names:
            if self.index in self.hub.where(name):
                self.dirty.add(name)
            self.dirty.update(o for o, v in self.views.items() if name in v.overlays)
        if self.dirty - set(self.views):
            self.sync_views()
        elif not self.views:
            self.grid.setText(self._empty_text())  # the output went to another view

    def _empty_text(self):
        if self.hub.names():
            return f"Nothing placed in {self.title}: right-click to choose outputs"
        return "No live data yet: it comes with the next count"

    def _make_view(self, name):
        view = self.views[name] = FrameView(
            name,
            extra_menu=self._panel_menu,
            history=self.hub.series_for(name),
        )
        # The state saved for this panel wins over the state that any panel
        # kept last.
        states = self.hub.states_of(name)
        if state := states.get(str(self.index), states.get("last")):
            view.restore(state)
        view.changed.connect(lambda: self._keep_state(name, view))
        view.hide_requested.connect(lambda: self.set_hidden(name, True))
        view.overlays_changed.connect(lambda: self._draw(name))
        view.arm_chosen.connect(self.set_tool)
        view.arm(self.tool)
        self.canvases[name] = FrameCanvas(view)
        self.canvases[name].setParent(self)
        self.solo.add(self.canvases[name])
        self.dirty.add(name)

    def _keep_state(self, name, view):
        state = view.state()
        self.hub.states_of(name).update({str(self.index): state, "last": state})

    def _drop_view(self, name):
        self.dirty.discard(name)
        self._keep_state(name, self.views.pop(name))
        canvas = self.canvases.pop(name)
        canvas.setParent(None)
        canvas.deleteLater()
        self.solo.remove(canvas)

    def shown(self, alone=True):
        if alone and (solo := [n for n, view in self.views.items() if view.solo]):
            return solo
        names = [n for n in self.order if n in self.views]
        for name in sorted(set(self.views) - set(names)):
            # a derived plot such as "ngem.roi0" goes after the plot of "ngem"
            base = name.split(".")[0]
            ours = [i for i, n in enumerate(names) if n.split(".")[0] == base]
            names.insert(ours[-1] + 1 if ours else len(names), name)
        return names

    def place(self, name, after):
        """Put plot *name* after plot *after*, or first if *after* is None."""
        names = [n for n in self.shown() if n != name]
        names.insert(names.index(after) + 1 if after else 0, name)
        self.order = names + [n for n in self.order if n not in names]
        self.relayout()

    def relayout(self):
        """Lay out all plots in a grid.

        When one plot is shown alone, the other plots and the empty rows are
        hidden so that the grid keeps its sizes.
        """
        shown = self.shown(alone=False)
        cols = grid_columns(len(shown), self.width(), self.height())
        if shown and (shown, cols) == (self._shown, self._cols):
            return self._show_alone()
        self._remember_split()
        self._shown, self._cols = shown, cols
        self.tool_bar.setEnabled(bool(shown))
        for canvas in self.canvases.values():
            # the canvas must survive the deletion of the old grid
            canvas.setParent(self)
        if shown:
            rows = [
                splitter(
                    Qt.Orientation.Horizontal,
                    [self.canvases[n] for n in shown[i : i + cols]],
                )
                for i in range(0, len(shown), cols)
            ]
            grid = splitter(Qt.Orientation.Vertical, rows)
            self._key = f"{'/'.join(shown)}|{cols}"
            state = self.split_states.get(self._key, {})
            for split, sizes in zip(
                [grid, *rows], [state.get("rows"), *state.get("cols", [])], strict=False
            ):
                if sizes and len(sizes) == split.count():
                    split.setSizes(sizes)
        else:
            grid = QLabel(self._empty_text())
            grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            grid.customContextMenuRequested.connect(self._empty_menu)
            self._key = None
        self.layout().replaceWidget(self.grid, grid)
        self.grid.deleteLater()
        self.grid = grid
        self._show_alone()
        self.draw_dirty()

    def _show_alone(self):
        alone = self.shown()
        for name, canvas in self.canvases.items():
            canvas.setVisible(name in alone)
        for row in self._rows() if self._key else []:
            shown = any(not row.widget(i).isHidden() for i in range(row.count()))
            row.setVisible(shown)

    def _empty_menu(self, _pos):
        menu = QMenu()
        self._layout_entries(menu)
        if not menu.isEmpty():
            menu.exec(QCursor.pos())

    def _rows(self):
        return [self.grid.widget(i) for i in range(self.grid.count())]

    def _remember_split(self):
        if self._key is not None and not any(v.solo for v in self.views.values()):
            self.split_states[self._key] = dict(
                rows=self.grid.sizes(), cols=[row.sizes() for row in self._rows()]
            )

    def equal_sizes(self):
        """Give all rows and plots equal sizes again."""
        self.split_states.pop(self._key, None)
        for split in [self.grid, *self._rows()]:
            split.setSizes([EQUAL] * split.count())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.relayout()

    def set_hidden(self, name, hidden):
        self.hub.show_in(name, self.index, not hidden)

    def show_all(self):
        self.solo.show(None)
        self.hub.show_everything_in(self.index)

    def _panel_menu(self, entries, view):
        """Add the curves to overlay and the layout entries to the menu of a plot."""
        hub = self.hub
        if view.view is not None and view.view.data.ndim == 1:
            others = {n for n, (f, _t) in hub.outputs.items() if len(f.dims) == 1}
            others = sorted((others | set(view.overlays)) - {view.name})

            def overlay(menu):  # A checked curve is drawn over this plot.
                for name in others:
                    add = partial(view.set_overlay, name)
                    check_action(menu, name, name in view.overlays, add)

            if others:
                entries["Curves"] = overlay
        layout = lambda menu: self._layout_entries(menu, view)  # noqa: E731
        entries["Layout"] = submenu(f"Plots in {self.title}", layout)

    def _layout_entries(self, menu, view=None):
        """Add entries that choose the plots of the panel and where *view* goes."""
        hub = self.hub
        for name in hub.names():
            on = self.index in hub.where(name)
            check_action(menu, name, on, lambda on, n=name: self.set_hidden(n, not on))
        if hub.names():
            menu.addAction("All of them").triggered.connect(self.show_all)
            menu.addSeparator()
        if view is not None and len(hub.indices()) > 1:
            move, also = menu.addMenu("Move to"), menu.addMenu("Also show in")
            for index in [i for i in hub.indices() if i != self.index]:
                title, on = hub.title(index), index in hub.where(view.name)
                move.addAction(title, partial(hub.move, view.name, index))
                check_action(also, title, on, partial(hub.show_in, view.name, index))
        if view is not None and not view.solo and len(self.views) > 1:
            place = menu.addMenu("Place")
            place.addAction("First", partial(self.place, view.name, None))
            for name in [n for n in self.shown() if n != view.name]:
                place.addAction(f"After {name}", partial(self.place, view.name, name))
        if len(self._shown) > 1:
            menu.addAction("Equal plot sizes").triggered.connect(self.equal_sizes)

    def _draw(self, name):
        self.dirty.discard(name)
        if name not in self.hub.outputs:
            return
        view = self.views[name]
        frame, received = self.hub.outputs[name]
        outputs = self.hub.outputs
        view.overlay_frames = {o: outputs[o][0] for o in view.overlays if o in outputs}
        view.show_frame(frame, received)

    def draw_dirty(self):
        """Draw the shown plots that changed, the longest waiting first.

        Drawing stops after DRAW_BUDGET and the rest is drawn on the next ticks.
        """
        if self.isVisible():
            start = time.monotonic()
            for name in sorted(
                self.dirty & set(self.shown()), key=self.drawn.__getitem__
            ):
                if time.monotonic() - start > DRAW_BUDGET:
                    break
                self.drawn[name] = start
                self._draw(name)

    def update_ages(self):
        """Mark the plots whose outputs lag behind the newest output."""
        if self.isVisible():
            hub = self.hub
            newest = max((t for _f, t in hub.outputs.values()), default=0)
            for name in self._shown:
                # time spent in a pause is not lag
                lag = newest - max(hub.outputs[name][1], hub.resumed)
                view = self.views[name]
                view.period = hub.periods.get(name, 0)
                view.lagging = lag > max(LAG, 3 * view.period)

    def saveSettings(self, settings):
        for name, view in self.views.items():
            self._keep_state(name, view)
        self._remember_split()
        splits = {self._key: self.split_states[self._key]} if self._key else {}
        saved = dict(splits=splits, order=self.order)
        settings.setValue("liveview", json.dumps(saved))
        self.hub.save()

    def loadSettings(self, settings):
        raw = settings.value("liveview")
        try:
            self._saved = json.loads(raw) if raw else {}
        except (TypeError, ValueError):
            self._saved = {}
