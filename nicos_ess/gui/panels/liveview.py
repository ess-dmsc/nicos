"""The live view panel shows all live data outputs as a grid of plots.

Several live views with ``index`` 1, 2 and so on share one `LiveHub` per
connection. New outputs go to the view with the lowest index. The user drags
plots by their titles to arrange them or to move them to another view, and
the plot menu can also move an output or show it in several views. While the
panel is visible, a timer redraws the plots whose outputs changed. The tool bar
selects pan/zoom or a measurement tool, and Esc goes back to pan/zoom.
"""

from __future__ import annotations

import collections
import json
import time
from functools import partial

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QActionGroup,
    QCursor,
    QKeySequence,
    QMenu,
    QShortcut,
    Qt,
    QTimer,
    QToolBar,
    QVBoxLayout,
)
from nicos_ess.gui.live_hub import hub_for
from nicos_ess.gui.panels.live_grid import LiveGrid
from nicos_ess.gui.widgets.pyqtgraph.frame_plot import FrameCanvas, FrameView, Solo
from nicos_ess.gui.widgets.pyqtgraph.measure_editor import KINDS
from nicos_ess.gui.widgets.pyqtgraph.plot_parts import check_action, submenu
from nicos_ess.utilities.grid_layout import arrange, automatic, from_preset, pack

REDRAW_MS = 100
# Drawing stops after this many seconds per tick so that the GUI still
# handles user input.
DRAW_BUDGET = 0.05
CELL_ASPECT = 1.4  # plots should be about this much wider than high
# An output is out of date when it is more than LAG seconds or three of its
# periods behind the newest output.
LAG = 10
TOOL_BAR_STYLE = (
    "QToolBar { spacing: 2px; padding: 2px 4px; }"
    " QToolBar > QToolButton { padding: 1px 8px; }"
)


def saved_spans(saved):
    """Return the spans of the plots in the saved settings of a panel.

    Damaged spans and repeated names are left out.
    """
    grid = saved.get("grid") if isinstance(saved, dict) else None
    spans = {}
    for span in grid if isinstance(grid, list) else []:
        if not (isinstance(span, list) and len(span) == 3):
            continue
        name, w, h = span
        ints = type(w) is int and type(h) is int  # True is an int too
        if isinstance(name, str) and ints and name not in spans:
            spans[name] = (name, w, h)
    return list(spans.values())


class LiveViewPanel(Panel):
    """The panel shows a live view of the outputs placed in it.

    The options are ``index`` with default 1 and ``title`` with default
    "Live <index>". The option ``layout`` places the plots until the user
    arranges them. It maps output names or fnmatch wildcards to cells
    (x, y, width, height) on a grid of 12 columns, where the rows share the
    height of the panel. The plots keep the order of these cells, and the rules
    of `grid_layout` close any gaps between them. The option ``outputs`` lists
    names or wildcards of the outputs that go to this view unless the user
    placed them.
    """

    panelName = "Live view"

    def __init__(self, parent, client, options):
        self.index = int(options.get("index", 1))
        self.title = options.get("title") or f"Live {self.index}"
        layout = dict(options.get("layout") or {})
        self.preset = {k: cell for k, cell in layout.items() if len(cell) == 4}
        outputs = options.get("outputs") or []
        self.outputs = [outputs] if isinstance(outputs, str) else list(outputs)
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
        # The spans (name, w, h) of the plots are in the order the user put
        # them. They also keep the places of outputs that are gone for now.
        self.spans = saved_spans(self._saved)
        self.tool = None  # None means pan/zoom
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.tool_bar = self._tool_bar()
        layout.addWidget(self.tool_bar)
        self.grid = LiveGrid(self.index)
        self.grid.arranged.connect(self.keep_arrangement)
        self.grid.dropped.connect(self.take_dropped)
        self.grid.ended.connect(self.sync_views)
        self.grid.show_all.connect(lambda: self.solo.show(None))
        self.grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self._empty_menu)
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
        if self.grid.session is not None:
            return  # the grid calls this again when the drag has ended
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
        elif not self.views and self.grid.empty_text != self._empty_text():
            self.relayout()  # the first output went to another view

    def _empty_text(self):
        if self.hub.names():
            return f"Nothing placed in {self.title}. Right-click or drag plots here."
        return "No live data yet. It comes with the next count."

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
        view.title_item.dragged.connect(partial(self.grid.title_drag, name))
        view.title_item.set_draggable()
        view.arm(self.tool)
        self.canvases[name] = FrameCanvas(view)
        self.grid.add(name, self.canvases[name])
        self.solo.add(self.canvases[name])
        self.dirty.add(name)

    def _keep_state(self, name, view):
        state = view.state()
        self.hub.states_of(name).update({str(self.index): state, "last": state})

    def _drop_view(self, name):
        self.dirty.discard(name)
        self.drawn.pop(name, None)
        self._keep_state(name, self.views.pop(name))
        canvas = self.canvases.pop(name)
        self.grid.remove(name)
        canvas.deleteLater()
        self.solo.remove(canvas)

    def solo_name(self):
        """Return the name of the plot that is shown alone, or None."""
        return next((n for n, view in self.views.items() if view.solo), None)

    def shown(self):
        solo = self.solo_name()
        return [solo] if solo else sorted(self.views)

    def arrangement(self, names):
        """Return the cells of *names* as the user, the guiconfig or the shape of
        the panel places them.
        """
        if self.spans:
            return arrange(names, self.spans)
        if spans := from_preset(names, self.preset):
            return arrange(names, spans)
        width, height = self.grid.width(), self.grid.height()
        return pack(automatic(names, width, height, CELL_ASPECT))

    def relayout(self):
        """Put the plots into their cells, or show the one plot shown alone."""
        shown = sorted(self.views)
        self.tool_bar.setEnabled(bool(shown))
        self.grid.empty_text = "" if shown else self._empty_text()
        self.grid.set_cells(self.arrangement(shown), self.solo_name())
        self.draw_dirty()

    def keep_arrangement(self, spans):
        """Keep the layout *spans* that the user made.

        The plots of outputs that are gone for now keep their places in the list.
        """
        names = {name for name, _w, _h in spans}
        spans = list(spans)
        for i, span in enumerate(self.spans):
            if span[0] not in names:
                spans.insert(min(i, len(spans)), span)
        self.spans = spans
        self.relayout()

    def take_dropped(self, name, copy, source):
        """Show the output *name* dropped here from the view *source*.

        A copy also stays in *source*, and a move takes it only from there.
        """
        if copy:
            self.hub.show_in(name, self.index, True)
        else:
            self.hub.move(name, self.index, source)

    def reset_layout(self):
        self.spans = []
        self.relayout()

    def _empty_menu(self, pos):
        if self.grid.childAt(pos) is not None:
            return  # a right click on a plot opens the plot's own menu
        menu = QMenu()
        self._layout_entries(menu)
        if not menu.isEmpty():
            menu.exec(QCursor.pos())

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
                move.addAction(title, partial(hub.move, view.name, index, self.index))
                check_action(also, title, on, partial(hub.show_in, view.name, index))
        if self.views:
            reset = menu.addAction("Reset layout", self.reset_layout)
            reset.setEnabled(bool(self.spans))
            reset.setToolTip("Go back to the layout of the instrument")

    def _draw(self, name):
        self.dirty.discard(name)
        if name not in self.hub.outputs:
            return
        view = self.views[name]
        frame, received = self.hub.outputs[name]
        outputs = self.hub.outputs
        view.overlay_frames = {o: outputs[o][0] for o in view.overlays if o in outputs}
        view.show_frame(frame, received)
        self.grid.refresh(name)

    def draw_dirty(self):
        """Draw the shown plots that changed, the longest waiting first.

        Drawing stops after DRAW_BUDGET and the rest is drawn on the next ticks.
        While pictures cover the plots during a drag and its animations, only
        the dragged plot and new plots are drawn, so the animations stay smooth.
        """
        if self.isVisible():
            start = time.monotonic()
            shown = set(self.shown())
            if self.grid.layer.isVisible():
                dragged = getattr(self.grid.session, "name", None)
                shown = {n for n in shown if n == dragged or not self.drawn.get(n)}
            for name in sorted(self.dirty & shown, key=self.drawn.__getitem__):
                if time.monotonic() - start > DRAW_BUDGET:
                    break
                self.drawn[name] = start
                self._draw(name)

    def update_ages(self):
        """Mark the plots whose outputs lag behind the newest output."""
        if self.isVisible():
            hub = self.hub
            newest = max((t for _f, t in hub.outputs.values()), default=0)
            for name in self.views:
                # A drag keeps the plot of a forgotten output until it ends.
                if name not in hub.outputs:
                    continue
                # time spent in a pause is not lag
                lag = newest - max(hub.outputs[name][1], hub.resumed)
                view = self.views[name]
                view.period = hub.periods.get(name, 0)
                view.lagging = lag > max(LAG, 3 * view.period)

    def saveSettings(self, settings):
        for name, view in self.views.items():
            self._keep_state(name, view)
        settings.setValue("liveview", json.dumps(dict(grid=self.spans)))
        self.hub.save()

    def loadSettings(self, settings):
        raw = settings.value("liveview")
        try:
            self._saved = json.loads(raw) if raw else {}
        except (TypeError, ValueError):
            self._saved = {}
