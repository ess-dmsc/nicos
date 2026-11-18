"""The view box of a `FrameView`, which handles tools, Shift + wheel and clicks."""

import pyqtgraph as pg
from pyqtgraph.graphicsItems.ROI import Handle

from nicos.guisupport.qt import QGraphicsRectItem, Qt

LEFT = Qt.MouseButton.LeftButton


class DrawSurface(QGraphicsRectItem):
    """A transparent item that covers the view box while a tool is armed.

    pyqtgraph gives a drag to the item that accepted it on hover, as
    measurements do. This item takes drags first, so a drag draws a new
    shape instead of moving an existing one. Its cursor is a cross over an
    image, which the tools measure, and a hand over a measurement's label.
    """

    def __init__(self, vb):
        super().__init__(vb)
        self.vb, self.owner = vb, vb.owner
        self.setPen(pg.mkPen(None))
        self.setZValue(1e9)
        self.hide()
        vb.sigResized.connect(lambda: self.setRect(vb.rect()))

    def hoverEvent(self, ev):
        if ev.isExit():
            return
        # A drag on a handle or a movable line moves that item instead.
        under = self.scene().items(ev.scenePos())
        if any(isinstance(i, Handle) or getattr(i, "movable", 0) for i in under):
            return self.unsetCursor()
        ev.acceptDrags(LEFT)
        ev.acceptClicks(LEFT)
        if self.owner.measure.label_at(ev.scenePos()) is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self.owner.image is not None:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.unsetCursor()

    def mouseDragEvent(self, ev):
        self.vb.mouseDragEvent(ev)

    def mouseClickEvent(self, ev):
        self.vb.mouseClickEvent(ev)


class PlotViewBox(pg.ViewBox):
    """A view box that passes mouse events to the tools of the plot.

    A double-click shows the plot alone or shows all plots again.
    """

    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.start = None
        self.surface = DrawSurface(self)

    def mouseClickEvent(self, ev):
        owner, left, double = self.owner, ev.button() == LEFT, ev.double()
        # A double-click shows the plot alone, so it cancels the label menu.
        owner.measure.cancel_menu()
        label = owner.measure.label_at(ev.scenePos()) if left else None
        point = self.mapSceneToView(ev.scenePos())
        if label is not None and not double:
            owner.measure.open_menu_later(label, ev.screenPos().toPoint())
        elif left and not double and owner.armed == "crosshair":
            if not owner.measure.measure_at(point.x(), point.y()):
                return super().mouseClickEvent(ev)
        elif left and double:
            owner.solo_requested.emit()
        else:
            return super().mouseClickEvent(ev)
        ev.accept()

    def mouseDragEvent(self, ev, axis=None):
        armed = self.owner.armed
        if armed and ev.button() == LEFT and self.owner.image is None:
            ev.accept()  # There is nothing to measure, and an armed tool must not pan.
        elif armed and ev.button() == LEFT:
            if ev.isStart():
                # Data coordinates keep the start in place when the view changes.
                self.start = self.mapSceneToView(ev.buttonDownScenePos())
            end = self.mapSceneToView(ev.scenePos())
            if armed in ("box", "line") and self.owner.measure.measure_between(
                armed, self.start, end, done=ev.isFinish()
            ):
                ev.accept()
        if not ev.isAccepted():
            super().mouseDragEvent(ev, axis)

    def suggestPadding(self, axis):
        """Leave no padding on a time axis, where the right edge is the current time."""
        if axis == 0 and isinstance(self.owner.plot.getAxis("bottom"), pg.DateAxisItem):
            return 0.0
        return super().suggestPadding(axis)

    def childrenBounds(self, *args, **kwargs):
        """Give flat data a span around its value, and cut the bounds to the
        limits of the view box.

        Otherwise pyqtgraph keeps the previous range, and bounds wider than its
        limits of 1e307 give a range of NaN.
        """
        bounds = super().childrenBounds(*args, **kwargs)
        if bounds[1] is not None and bounds[1][0] == bounds[1][1]:
            half = abs(bounds[1][0]) * 0.1 or 1.0
            bounds[1] = [bounds[1][0] - half, bounds[1][1] + half]
        limits = self.state["limits"]["xLimits"], self.state["limits"]["yLimits"]
        return [
            b and [min(max(v, low), high) for v in b]
            for b, (low, high) in zip(bounds, limits, strict=True)
        ]

    def wheelEvent(self, ev, axis=None):
        shift = ev.modifiers() & Qt.KeyboardModifier.ShiftModifier
        if shift and self.owner.step_window(1 if ev.delta() > 0 else -1):
            ev.accept()
        else:
            super().wheelEvent(ev, axis)
