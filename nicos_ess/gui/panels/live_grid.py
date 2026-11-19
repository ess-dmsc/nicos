"""Plots in cards on a grid that the user arranges with the mouse.

`nicos_ess.utilities.grid_layout` has the rules of the layout. The user drags
a plot by its title and resizes it at its right edge, its bottom edge or its
corner. Redrawing a pyqtgraph plot at a new size takes 10 to 100 ms, so while
the button is down a layer over the grid shows pictures of the plots, and the
plots take their new places only at the drop. A plot dragged out of the panel
becomes a Qt drag that other live views accept.
"""

from __future__ import annotations

import time

from nicos.guisupport.qt import (
    QApplication,
    QColor,
    QCursor,
    QDrag,
    QEasingCurve,
    QEvent,
    QMimeData,
    QMouseEvent,
    QPainter,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QTabWidget,
    QTimer,
    QVariantAnimation,
    QWidget,
    pyqtSignal,
    sip,
)
from nicos_ess.gui.panels.live_cards import (
    CURSORS,
    MIME,
    Grip,
    Layer,
    Lift,
    LiveCard,
    drag_picture,
    dropped_plot,
    paint_shadow,
    paint_styled,
    plot_mime,
)
from nicos_ess.utilities.grid_layout import (
    COLUMNS,
    MIN_WIDTH,
    Cell,
    add,
    bottom,
    find,
    insert,
    new_row,
    pack,
    resize,
    spans_of,
    swap,
)

GAP = 8  # pixels between the cards and around them
SLIDE_MS = 180
FADE_MS = 120
SETTLE_MS = 60  # the plots get this long to paint under the layer
SWITCH_MS = 500  # hovering a dragged plot this long over a tab opens the tab
NEW_ROW = 36  # a plot dropped this close to the bottom starts a new row
REFRESH_S = 0.25  # the picture of the dragged plot follows its data this often
DRAGGING = ("move", "resize")


def switch_bars(widget):
    """Return the tab bars around *widget* that open a tab when a plot hovers on it.

    A QTabWidget offers its tab bar. Another container can offer its own bars
    with a method ``plot_switch_bars()``. A bar needs ``tabAt(pos)`` and
    ``setCurrentIndex(index)`` like a QTabBar.
    """
    bars = []
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QTabWidget):
            bars.append(parent.tabBar())
        if hasattr(parent, "plot_switch_bars"):
            bars.extend(parent.plot_switch_bars())
        parent = parent.parentWidget()
    return bars


class Session:
    """A move, a resize, or a Qt drag of a plot over the grid.

    *kind* is "move" or "resize" while the pointer drags inside the panel,
    "away" while a plot of this grid is in a Qt drag elsewhere and "drop"
    while a Qt drag is over the grid. *key* names what a drop would do now.
    """

    def __init__(self, kind, name, cells, rows, press=None, edge=None, frame=None):
        self.kind = kind
        self.name = name
        self.edge = edge
        self.press = press
        self.start = list(cells)
        self.cells = list(cells)
        self.rows = rows
        self.frame = frame
        self.key = None
        self.source = None


def _cells_after_drop(start, name, target):
    """Return the cells that dropping *name* on *target* gives, or None if it
    does not fit."""
    kind = target[0]
    if kind == "start":
        return start
    if kind == "swap":
        return pack(swap(start, name, target[1]))
    if kind == "insert":
        spans = insert(start, name, *target[1:])
        return None if spans is None else pack(spans)
    if kind == "row":
        mine = find(start, name)
        return pack(new_row(start, name, mine.h if mine else 1))
    if kind == "add":
        return pack(add(start, name))
    return resize(start, name, *target[1:])


class LiveGrid(QWidget):
    """Cards of plots on a grid of `COLUMNS` columns that fills the widget.

    The owner passes the cells to `set_cells` and gets the spans of a layout
    that the user made from ``arranged``. ``dropped`` sends the name of a plot
    dropped here from another view, whether to copy it and the index of that
    view. The owner waits with changes until ``ended``. A drag of the plot
    that is shown alone emits ``show_all``, and the owner shows all plots
    before the drag goes on.
    """

    arranged = pyqtSignal(object)
    dropped = pyqtSignal(str, bool, int)
    ended = pyqtSignal()
    show_all = pyqtSignal()

    def __init__(self, index=0, parent=None):
        super().__init__(parent)
        self.index = index
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setAcceptDrops(True)
        self.cards, self.cells, self.solo, self.empty_text = {}, [], None, ""
        # The layer paints the pictures in the rects shown. After a drop it
        # fades into fresh pictures of the plots that were resized.
        self.pixmaps, self.fresh, self.shown, self.animations = {}, {}, {}, {}
        self.resized, self._refreshed = set(), 0.0
        # The lifted card is drawn above the whole window, and the raised card
        # is drawn above the other cards.
        self.session = self.ghost = self.lifted = self.raised = self.lift = None
        self.hovered = self._pressed = self._tab = None
        self.grips = {edge: Grip(self, edge) for edge in CURSORS}
        self.layer = Layer(self)
        self.fade = QVariantAnimation(self, duration=FADE_MS, startValue=1.0)
        self.fade.setEndValue(0.0)
        self.fade.valueChanged.connect(self._set_opacity)
        self.fade.finished.connect(self._hide_layer)
        self.tab_timer = QTimer(self, singleShot=True, interval=SWITCH_MS)
        self.tab_timer.timeout.connect(self._switch_tab)

    def add(self, name, canvas):
        self.cards[name] = card = LiveCard(canvas)
        card.setParent(self)
        card.installEventFilter(self)
        card.hide()  # place_cards shows the card in its cell.

    def remove(self, name):
        if self.session is not None and name in (self.session.name, *self.pixmaps):
            self.cancel(animate=False)
        card = self.cards.pop(name)
        card.canvas.setParent(None)
        card.deleteLater()
        if self.hovered == name:
            self.show_grips(None)

    def set_cells(self, cells, solo=None):
        """Show the cards of *cells*, or only *solo*, when the layer is down."""
        self.cells, self.solo = list(cells), solo
        if self.layer.isHidden():
            self.place_cards()
        self.update()

    def rows(self):
        return max(bottom(self.cells), 1)

    def frame(self, cell, rows=None):
        """Return the rectangle of *cell* in pixels."""
        rows = rows or self.rows()
        dx, dy = (self.width() - GAP) / COLUMNS, (self.height() - GAP) / rows
        left, top = round(GAP + cell.x * dx), round(GAP + cell.y * dy)
        right, low = round((cell.x + cell.w) * dx), round((cell.y + cell.h) * dy)
        return QRect(left, top, right - left, low - top)

    def frames(self):
        """Return the rect of each shown card in its cell."""
        if self.solo in self.cards:
            return {self.solo: QRectF(self.frame(Cell(self.solo, 0, 0, COLUMNS, 1), 1))}
        rows, cells = self.rows(), [c for c in self.cells if c.name in self.cards]
        return {c.name: QRectF(self.frame(c, rows)) for c in cells}

    def place_cards(self):
        """Move the real cards to their cells. This lays out the plots again."""
        frames = self.frames()
        for name, card in self.cards.items():
            if name in frames:
                card.setGeometry(frames[name].toRect())
            card.setVisible(name in frames)
        self.hover_check()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.layer.setGeometry(self.rect())
        self.cancel(animate=False)
        self.place_cards()

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_styled(painter, self, self.rect())
        painter.setPen(QColor("#555"))
        if not self.cards:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.empty_text)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for card in self.cards.values():
            if card.isVisible():
                paint_shadow(painter, card.geometry(), 3)

    def showEvent(self, event):
        """Let the tab bars around the grid open their tabs for a dragged plot."""
        super().showEvent(event)
        for bar in switch_bars(self):
            if not bar.property("liveTabSwitch"):
                bar.setProperty("liveTabSwitch", True)
                bar.setAcceptDrops(True)
                bar.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Follow the pointer over the cards, the tab bars and during a drag."""
        if obj.property("liveTabSwitch"):
            return self._tab_event(obj, event)
        if self.session is not None and self.session.kind in DRAGGING:
            return self._drag_event(obj, event)
        hover = event.type() in (QEvent.Type.Enter, QEvent.Type.Leave)
        if hover and isinstance(obj, LiveCard):
            # Check the hover after Qt has sent both the Leave and the Enter event.
            QTimer.singleShot(0, self.hover_check)
        return False

    def _drag_event(self, obj, event):
        """End a drag on Esc or when the button is up, wherever it was released."""
        kind = event.type()
        if kind in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress):
            # Esc is also a shortcut of the panel, and a shortcut gets the key
            # before any widget does.
            if event.key() == Qt.Key.Key_Escape:
                event.accept()
                self.cancel()
                return True
        elif not isinstance(obj, QWidget):
            return False
        elif kind == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                self.drop()
        elif kind == QEvent.Type.MouseMove and self.session.kind == "resize":
            if event.buttons() & Qt.MouseButton.LeftButton:
                self.drag_to(event.globalPos())
            else:
                self.drop()
        return False

    def _tab_event(self, bar, event):
        kind = event.type()
        over = (QEvent.Type.DragEnter, QEvent.Type.DragMove)
        if kind in (*over, QEvent.Type.Drop) and not event.mimeData().hasFormat(MIME):
            return False
        if kind in over:
            event.accept()
            if (bar, bar.tabAt(event.pos())) != self._tab:
                self._tab = (bar, bar.tabAt(event.pos()))
                self.tab_timer.start()
            return True
        if kind in (QEvent.Type.DragLeave, QEvent.Type.Drop):
            self.tab_timer.stop()
            self._tab = None
            event.ignore()
            return kind == QEvent.Type.Drop
        return False

    def _switch_tab(self):
        if self._tab is not None:
            self._tab[0].setCurrentIndex(self._tab[1])

    def hover_check(self):
        at = self.mapFromGlobal(QCursor.pos())
        near = [
            name
            for name, card in self.cards.items()
            if card.isVisible()
            and card.geometry().adjusted(-GAP, -GAP, GAP, GAP).contains(at)
        ]
        self.show_grips(near[0] if near else None)

    def show_grips(self, name):
        if self.session is not None:
            return  # A grip that holds the mouse must stay.
        before = self.hovered
        self.hovered = None if self.solo is not None or name not in self.cards else name
        for shown in {before, self.hovered} & self.cards.keys():
            title = self.cards[shown].canvas.view.title_item
            title.show_grip(shown == self.hovered)
        if self.hovered is None:
            for grip in self.grips.values():
                grip.hide()
            return
        r, side = self.cards[name].geometry(), GAP // 2
        places = {
            "s": QRect(r.left() + 2 * GAP, r.bottom() - side, r.width() - 4 * GAP, GAP),
            "e": QRect(r.right() - side, r.top() + 2 * GAP, GAP, r.height() - 4 * GAP),
            "se": QRect(r.right() - 2 * GAP + 2, r.bottom() - 2 * GAP + 2, 16, 16),
        }
        for edge, grip in self.grips.items():
            grip.setGeometry(places[edge])
            grip.show()
            grip.raise_()

    def title_drag(self, name, press, at, phase):
        """Follow a drag of the title of plot *name* between screen positions."""
        if phase == "start":
            self._pressed = name
        far = (at - press).manhattanLength() >= QApplication.startDragDistance()
        if self.session is None and phase != "finish" and far:
            if self._pressed == name:
                self._pressed = None
                self.start("move", name, press.toPoint())
                self.drag_to(at.toPoint())
        elif self.session is not None and self.session.name == name:
            # The release ends the drag in the event filter.
            self.drag_to(at.toPoint())

    def start(self, kind, name, press, edge=None):
        """Start to move or resize the plot *name* from the screen position *press*."""
        alone = self.frames()[name] if self.solo == name else None
        if alone is not None and self.session is None and kind == "move":
            self.show_all.emit()
        if self.session is not None or name not in self.cards or self.solo is not None:
            return
        frame = self.frame(find(self.cells, name))
        press = self.mapFromGlobal(press)
        if alone is not None:
            # The card in its cell is smaller, so it moves under the pointer.
            held = press - alone.topLeft().toPoint()
            frame.moveTopLeft(
                press - QPoint(min(held.x(), frame.width() // 2), held.y())
            )
        self._begin(Session(kind, name, self.cells, self.rows(), press, edge, frame))
        self.shown[name] = QRectF(frame)
        if kind == "move":
            self.lifted = name
            self.lift.follow()
        else:
            self.raised = name
        cursor = CURSORS.get(edge, Qt.CursorShape.ClosedHandCursor)
        QApplication.setOverrideCursor(cursor)

    def _begin(self, session):
        self.fade.stop()
        self._set_opacity(1.0)
        self.pixmaps.update(self.fresh)
        self.fresh = {}
        for animation in self.animations.values():
            animation.stop()
        if self.layer.isHidden():
            self.pixmaps, self.shown = {}, {}
        frames = self.frames()
        for name in frames.keys() - self.pixmaps.keys():
            # This may send the grid a resize event that ends any session.
            self.pixmaps[name] = self.cards[name].canvas.grab()
        # The lift lives in the window, which is gone when the user moved the
        # panel to another window and closed that one.
        lost = self.lift is None or sip.isdeleted(self.lift)
        if lost or self.lift.parentWidget() is not self.window():
            self.lift = Lift(self)
        self.session = session
        self.shown = {n: self.shown.get(n, r) for n, r in frames.items()}
        self.ghost = self.shown.get(session.name)
        self.layer.show()
        self.layer.raise_()
        QApplication.instance().installEventFilter(self)

    def refresh(self, name):
        """Take a new picture of the dragged plot *name* after it got new data."""
        session = self.session
        if session is None or session.name != name or name not in self.cards:
            return
        if time.monotonic() - self._refreshed > REFRESH_S:
            self._refreshed = time.monotonic()
            self.pixmaps[name] = self.cards[name].canvas.grab()
            self.lift.update()
            self.layer.update()

    def drag_to(self, at):
        """Follow the pointer at the screen position *at*."""
        session = self.session
        if session is None or session.kind not in DRAGGING:
            return
        pos = self.mapFromGlobal(at)
        delta = pos - session.press
        if session.kind == "resize":
            self._preview(("resize", *self._stretch(delta)))
            self.layer.update()
            return
        panel = self.parentWidget() or self
        if not panel.rect().contains(panel.mapFromGlobal(at)):
            self.hand_over()
            return
        self.shown[session.name] = QRectF(session.frame.translated(delta))
        self.lift.follow()
        self._preview(self._target(pos))

    def _target(self, pos):
        """Return what a drop at *pos* in the grid would do.

        None means that the target of the session stays as it is.
        """
        session = self.session
        if not self.rect().contains(pos):
            return ("start",)
        if pos.y() >= self.height() - NEW_ROW:
            return ("row",)
        mine = find(session.start, session.name)
        if mine is not None and self.frame(mine, session.rows).contains(pos):
            # The pointer is back over the place where the plot started, so
            # every plot goes back.
            return ("start",)
        for cell in session.cells:
            rect = self.frame(cell, session.rows)
            if cell.name != session.name and rect.contains(pos):
                other = find(session.start, cell.name)
                if mine is not None and (mine.w, mine.h) == (other.w, other.h):
                    return ("swap", cell.name)
                return ("insert", cell.name, pos.x() > rect.center().x())
        return None

    def _stretch(self, delta):
        """Return the span for a resize by *delta* and stretch the dragged card."""
        session = self.session
        dx, dy = (self.width() - GAP) / COLUMNS, (self.height() - GAP) / session.rows
        start = find(session.start, session.name)
        frame = QRectF(session.frame)
        if "e" in session.edge:
            right = min(frame.right() + delta.x(), self.width() - GAP)
            frame.setRight(max(right, frame.left() + MIN_WIDTH * dx - GAP))
        if "s" in session.edge:
            low = min(frame.bottom() + delta.y(), self.height() + dy / 2)
            frame.setBottom(max(low, frame.top() + dy - GAP))
        self.shown[session.name] = frame
        w = min(max(round((frame.width() + GAP) / dx), MIN_WIDTH), COLUMNS)
        h = min(max(round((frame.height() + GAP) / dy), 1), session.rows + 1 - start.y)
        return w, h

    def _preview(self, target):
        """Show the layout that a drop would give, if *target* is a new target."""
        session = self.session
        if target is None or target == session.key:
            return
        name = session.name
        cells = _cells_after_drop(session.start, name, target)
        if cells is None:
            return
        others = [c for c in cells if c.name != name]
        if target[0] != "resize" and bottom(others) > session.rows:
            return
        session.key, session.cells = target, cells
        self.slide(cells, session.rows)

    def slide(self, cells, rows):
        """Let the cards and the ghost glide to their places in *cells*."""
        session = self.session
        for cell in cells:
            target = QRectF(self.frame(cell, rows))
            if session is not None and cell.name == session.name:
                if cell.y >= rows:
                    # A new row shows as a strip at the bottom.
                    w, h = self.width() - 2 * GAP, NEW_ROW - GAP
                    target = QRectF(GAP, self.height() - NEW_ROW, w, h)
                self._glide(None, target)
            elif cell.name in self.shown:
                self._glide(cell.name, target)
        if session is not None and find(cells, session.name) is None:
            self.ghost = None
        self.layer.update()

    def _glide(self, name, target):
        """Animate the card *name*, or the ghost if *name* is None, to *target*."""
        current = self.ghost if name is None else self.shown.get(name)
        old = self.animations.get(name)
        running = old is not None and old.state() == QVariantAnimation.State.Running
        if running and old.endValue() == target or current == target and not running:
            return
        if old is not None:
            old.stop()
            old.deleteLater()
            del self.animations[name]
        if current is None:
            self._set_shown(name, target)
            return
        animation = self.animations[name] = QVariantAnimation(self)
        animation.setDuration(SLIDE_MS)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.setStartValue(current)
        animation.setEndValue(target)
        # The cyclic GC can clear a lambda slot while the C++ animation of a
        # closed window still runs, and every frame then raises a TypeError.
        # PyQt holds a bound method weakly and skips it once the grid is gone.
        animation.setProperty("card", name)
        animation.valueChanged.connect(self._animated)
        animation.start()

    def _animated(self, rect):
        self._set_shown(self.sender().property("card"), rect)

    def _set_shown(self, name, rect):
        if name is None:
            self.ghost = rect
        else:
            self.shown[name] = rect
            if name == self.lifted:
                self.lift.follow()
        self.layer.update()

    def drop(self):
        """Put the dragged plot where the ghost is."""
        if self.session is not None and self.session.kind in DRAGGING:
            self._finish()

    def _finish(self, copy=False):
        session = self.session
        self._end_session()
        if spans_of(session.cells) != spans_of(session.start):
            self.arranged.emit(spans_of(session.cells))
        if session.source is not None and session.source[0] != id(self):
            self.dropped.emit(session.name, copy, session.source[1])
        self.ended.emit()
        self._settle()

    def cancel(self, animate=True):
        """Put every plot back where it was before the drag."""
        if self.session is None:
            return
        self._end_session()
        # The owner may be in the middle of removing a plot.
        QTimer.singleShot(0, self.ended.emit)
        if animate:
            self._settle()
        else:
            self._close()
            self._hide_layer()

    def _end_session(self):
        session, self.session = self.session, None
        QApplication.instance().removeEventFilter(self)
        if session.kind in DRAGGING:
            QApplication.restoreOverrideCursor()
        if session.kind == "away" and session.name in self.shown:
            # The plot comes back into its gap if it was not dropped elsewhere.
            self.lifted = None
            self.shown[session.name] = QRectF(session.frame)

    def _settle(self):
        """Let every card glide into its cell, then close the layer."""
        frames = self.frames()
        self.shown = {n: r for n, r in self.shown.items() if n in frames}
        for name, rect in frames.items():
            if name in self.pixmaps:
                self._glide(name, rect)
        # A plot that came from another view has no picture, so the ghost
        # keeps its place until the plot shows.
        new = [rect for name, rect in frames.items() if name not in self.pixmaps]
        if new:
            self._glide(None, new[0])
        else:
            self.ghost = None
        self.layer.update()
        QTimer.singleShot(SLIDE_MS + 10, self._close)

    def _close(self):
        """Lay out the real cards under the layer and fade it out after they painted."""
        if not self._closing():
            return
        for animation in self.animations.values():
            animation.stop()
            animation.deleteLater()
        self.animations = {}
        self.lifted = self.raised = None
        if self.lift is not None:
            self.lift.hide()
        sizes = {name: card.size() for name, card in self.cards.items()}
        self.place_cards()
        self.resized = {n for n, c in self.cards.items() if c.size() != sizes[n]}
        # The plots lay themselves out on the next turn of the event loop.
        QTimer.singleShot(0, lambda: QTimer.singleShot(0, self._fade_out))

    def _fade_out(self):
        """Fade into fresh pictures of the plots that changed size, if any.

        A resized plot needs a few turns of the event loop to show its data.
        The layer stays opaque, because plots under a translucent layer paint
        late.
        """
        if self._closing() and self.fade.state() != QVariantAnimation.State.Running:
            if self.resized:
                QTimer.singleShot(SETTLE_MS, self._take_fresh)
            else:
                self._hide_layer()

    def _take_fresh(self):
        """Take one fresh picture per turn of the event loop, then fade."""
        if self._closing():
            frames = self.frames()
            todo = [name for name in frames if name in self.resized]
            if todo:
                self.fresh[todo[0]] = self.cards[todo[0]].canvas.grab()
                self.shown[todo[0]] = frames[todo[0]]
                self.resized.discard(todo[0])
                QTimer.singleShot(0, self._take_fresh)
            else:
                self.fade.start()

    def _closing(self):
        return self.session is None and not self.layer.isHidden()

    def _set_opacity(self, value):
        self.layer.opacity = value
        self.layer.update()

    def _hide_layer(self):
        if self.session is None:
            self.fade.stop()
            self.layer.hide()
            self.layer.opacity = 1.0
            self.pixmaps, self.shown, self.ghost, self.fresh = {}, {}, None, {}
            # The cells may have changed while the layer faded out.
            self.place_cards()

    def _away(self):
        """Keep the gap of the plot that is in a Qt drag elsewhere."""
        session = self.session
        session.kind, session.key, session.cells = "away", None, session.start
        self.slide(session.start, session.rows)
        self._glide(None, QRectF(session.frame))

    def hand_over(self):
        """Turn the drag of a plot that left the panel into a Qt drag."""
        name = self.session.name
        canvas = self.cards[name].canvas
        QApplication.restoreOverrideCursor()
        self.lift.hide()
        self._away()
        data = QMimeData()
        data.setData(MIME, plot_mime(self, name))
        data.setText(name)
        drag = QDrag(self)
        drag.setMimeData(data)
        drag.setPixmap(drag_picture(self.pixmaps[name]))
        # The picture hangs below right of the pointer, so the tab under the
        # pointer stays in sight.
        drag.setHotSpot(QPoint(-12, -16))
        done = drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)
        # pyqtgraph never saw the release that ended the Qt drag.
        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(canvas.viewport().mapFromGlobal(QCursor.pos())),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(canvas.viewport(), release)
        ended = self.session is not None
        if ended:
            self._end_session()
            if done == Qt.DropAction.MoveAction:
                self.shown.pop(name, None)
        self.ended.emit()
        if ended:
            self._settle()

    def dragEnterEvent(self, event):
        found = dropped_plot(event.mimeData())
        session = self.session
        mine = session is not None and session.kind == "away"
        if found is None or self.solo is not None or (session is not None and not mine):
            event.ignore()
            return
        source, index, name = found
        if mine and session.name == name:
            session.kind = "drop"
        else:
            if mine:
                self.cancel(animate=False)
            self._begin(Session("drop", name, self.cells, self.rows()))
            self.shown.pop(name, None)
        self.session.source = (source, index)
        self.dragMoveEvent(event)

    def dragMoveEvent(self, event):
        session = self.session
        if session is None or session.kind != "drop":
            event.ignore()
            return
        self._set_action(event)
        target = self._target(event.pos())
        if target in (None, ("start",)) and find(session.start, session.name) is None:
            target = session.key or ("add",)
        self._preview(target)

    def _set_action(self, event):
        """Accept the drop as a copy while Ctrl is held and return True for a copy."""
        held = event.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier
        copy = bool(held) and self.session.source[0] != id(self)
        action = Qt.DropAction.CopyAction if copy else Qt.DropAction.MoveAction
        event.setDropAction(action)
        event.accept()
        return copy

    def dragLeaveEvent(self, event):
        session = self.session
        if session is not None and session.kind == "drop":
            if session.source[0] == id(self):
                self._away()
            else:
                self.cancel()

    def dropEvent(self, event):
        if self.session is None or self.session.kind != "drop":
            event.ignore()
            return
        self._finish(self._set_action(event))
