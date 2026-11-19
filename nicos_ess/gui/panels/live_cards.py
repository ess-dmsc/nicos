"""The cards of the live grid, their grips, and the pictures that stand in for
the plots while the user drags them."""

from __future__ import annotations

import json
import os

from nicos.guisupport.qt import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPoint,
    QPointF,
    QRectF,
    QStyle,
    QStyleOption,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)

MIME = "application/x-nicos-live-plot"
INSET = 3  # pixels between the border of a card and its plot
RADIUS = 5
ACCENT = QColor("#0094ca")  # the accent colour of guiconfig.qss
GRIP = QColor("#a9a9a9")
DRAG_WIDTH = 200  # the width of the picture next to the pointer in a Qt drag
CURSORS = {
    "e": Qt.CursorShape.SizeHorCursor,
    "s": Qt.CursorShape.SizeVerCursor,
    "se": Qt.CursorShape.SizeFDiagCursor,
}


def plot_mime(grid, name):
    return json.dumps([os.getpid(), id(grid), grid.index, name]).encode()


def dropped_plot(data):
    """Return the grid id, view index and name of a plot dragged in this GUI.

    The names belong to the hub of this GUI, so other programs give None.
    """
    try:
        pid, *found = json.loads(bytes(data.data(MIME)).decode())
    except (ValueError, TypeError):
        return None
    return found if pid == os.getpid() else None


def paint_styled(painter, widget, rect):
    """Paint the style sheet background and border of *widget* into *rect*."""
    option = QStyleOption()
    option.initFrom(widget)
    option.rect = rect
    style = widget.style()
    style.drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, widget)


def paint_shadow(painter, rect, depth):
    painter.setPen(Qt.PenStyle.NoPen)
    for i in range(1, depth + 1):
        painter.setBrush(QColor(0, 0, 0, 14 - 10 * i // depth))
        grown = QRectF(rect).adjusted(-i / 2, i / 3, i / 2, i)
        painter.drawRoundedRect(grown, RADIUS + i / 2, RADIUS + i / 2)


def paint_picture(painter, pixmap, rect):
    """Paint *pixmap* into the card *rect* from its top left corner.

    The picture shrinks only until it covers the card and is cut at the right
    or the bottom, so the title stays readable. It never grows or squeezes.
    """
    inner = QRectF(rect).adjusted(INSET, INSET, -INSET, -INSET)
    # A card that is not laid out yet gives an empty picture, and so does a
    # card one row high when the rows are at most as high as the gap between cards.
    if pixmap is None or pixmap.isNull() or inner.width() < 1 or inner.height() < 1:
        return
    size = pixmap.size()
    scale = min(1.0, max(inner.width() / size.width(), inner.height() / size.height()))
    part = QRectF(0, 0, inner.width() / scale, inner.height() / scale)
    part = part.intersected(QRectF(pixmap.rect()))
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, scale < 1)
    painter.drawPixmap(QRectF(inner.topLeft(), part.size() * scale), pixmap, part)
    painter.restore()


def paint_card(painter, grid, name, rect, depth):
    """Paint the card *name*, fading from its old picture to its fresh one."""
    paint_shadow(painter, rect, depth)
    if (card := grid.cards.get(name)) is not None:
        paint_styled(painter, card, rect.toRect())
    old, fresh = grid.pixmaps.get(name), grid.fresh.get(name)
    painter.save()
    if fresh is not None:
        painter.setOpacity(1 if old else 1 - grid.layer.opacity)
        paint_picture(painter, fresh, rect)
        painter.setOpacity(grid.layer.opacity)
    paint_picture(painter, old, rect)
    painter.restore()


def drag_picture(pixmap):
    """Return a small translucent card with *pixmap* for a Qt drag."""
    smooth = Qt.TransformationMode.SmoothTransformation
    small = pixmap.scaledToWidth(min(DRAG_WIDTH, pixmap.width()), smooth)
    margin = 10
    out = QPixmap(small.width() + 2 * margin, small.height() + 2 * margin)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    card = QRectF(margin, margin, small.width(), small.height())
    paint_shadow(painter, card, 8)
    painter.setOpacity(0.88)
    path = QPainterPath()
    path.addRoundedRect(card, RADIUS, RADIUS)
    painter.setClipPath(path)
    painter.drawPixmap(card.topLeft(), small)
    painter.setClipping(False)
    painter.setPen(QPen(ACCENT, 1.5))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(card.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS, RADIUS)
    painter.end()
    return out


class LiveCard(QWidget):
    """The card around one plot. Its look comes from guiconfig.qss."""

    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(INSET, INSET, INSET, INSET)
        layout.addWidget(canvas)
        canvas.show()


class Grip(QWidget):
    """A handle on an edge or the corner of the card under the pointer."""

    def __init__(self, grid, edge):
        super().__init__(grid)
        self.grid, self.edge = grid, edge
        self.setCursor(CURSORS[edge])
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = ACCENT if self.underMouse() else GRIP
        painter.setPen(QPen(color, 2, cap=Qt.PenCapStyle.RoundCap))
        r = QRectF(self.rect())
        if self.edge == "se":
            for k in (4, 8):
                painter.drawLine(
                    QPointF(r.right() - k, r.bottom() - 3),
                    r.bottomRight() - QPointF(3, k),
                )
        elif self.edge == "s":
            painter.drawLine(r.center() - QPointF(12, 0), r.center() + QPointF(12, 0))
        else:
            painter.drawLine(r.center() - QPointF(0, 12), r.center() + QPointF(0, 12))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.grid.start("resize", self.grid.hovered, event.globalPos(), self.edge)

    def leaveEvent(self, event):
        QTimer.singleShot(0, self.grid.hover_check)


class Layer(QWidget):
    """Shows the pictures of the plots while the user drags."""

    def __init__(self, grid):
        super().__init__(grid)
        self.grid, self.opacity = grid, 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.hide()

    def paintEvent(self, event):
        grid, painter = self.grid, QPainter(self)
        paint_styled(painter, grid, self.rect())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for name, rect in grid.shown.items():
            if name not in (grid.lifted, grid.raised):
                paint_card(painter, grid, name, rect, 3)
        if grid.ghost is not None:
            painter.setOpacity(self.opacity)
            fill = QColor(ACCENT)
            fill.setAlphaF(0.18)
            painter.setPen(QPen(ACCENT, 1.5))
            painter.setBrush(fill)
            ghost = grid.ghost.adjusted(0.5, 0.5, -0.5, -0.5)
            painter.drawRoundedRect(ghost, RADIUS, RADIUS)
            painter.setOpacity(1)
        if grid.raised in grid.shown:
            paint_card(painter, grid, grid.raised, grid.shown[grid.raised], 10)
        if any(r.bottom() > self.height() for r in grid.shown.values()):
            # A fade at the bottom shows that plots were pushed below the grid.
            fade = QLinearGradient(0, self.height() - 40, 0, self.height())
            fade.setColorAt(0, QColor(238, 240, 242, 0))
            fade.setColorAt(1, QColor(238, 240, 242, 230))
            painter.fillRect(0, self.height() - 40, self.width(), 40, fade)


class Lift(QWidget):
    """The dragged card, above everything else in the window."""

    MARGIN = 14

    def __init__(self, grid):
        super().__init__(grid.window())
        self.grid = grid
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def follow(self):
        """Cover the rect of the lifted plot, or hide if there is none."""
        grid = self.grid
        rect = grid.shown.get(grid.lifted)
        if rect is None or (grid.session is not None and grid.session.kind != "move"):
            self.hide()
            return
        corner = QPointF(grid.mapTo(self.parentWidget(), QPoint(0, 0)))
        m = self.MARGIN
        self.setGeometry(rect.translated(corner).toAlignedRect().adjusted(-m, -m, m, m))
        self.show()
        self.raise_()
        self.update()

    def paintEvent(self, event):
        grid, painter = self.grid, QPainter(self)
        rect = grid.shown.get(grid.lifted)
        if rect is not None:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setOpacity(0.95)
            here = QRectF(self.MARGIN, self.MARGIN, rect.width(), rect.height())
            paint_card(painter, grid, grid.lifted, here, 10)
