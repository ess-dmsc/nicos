import numpy as np
from pyqtgraph import Point, mkBrush, mkPen
from pyqtgraph.graphicsItems.ROI import ROI
from pyqtgraph.graphicsItems.ROI import LineROI as DefaultLineROI

from nicos.guisupport.qt import QPainter, QPointF, QRectF, Qt
from nicos_ess.gui.widgets.pyqtgraph.theme import (
    LINE_ROI_COLOR,
    LINE_ROI_HANDLE_COLOR_LEFT,
    LINE_ROI_HANDLE_COLOR_RIGHT,
    LINE_ROI_HANDLE_HOOVER_COLOR_LEFT,
    LINE_ROI_HANDLE_HOOVER_COLOR_RIGHT,
    LINE_ROI_HOOVER_COLOR,
    LINE_ROI_WIDTH_COLOR,
)

Cursor = Qt.CursorShape


def _set_pens(handle, color, hover_color):
    handle.pen = handle.currentPen = mkPen(color, width=2)
    handle.hoverPen = mkPen(hover_color, width=2)


class PlotROI(ROI):
    """Box with scale handles on its corners and edges."""

    def __init__(self, size, *args, **kwargs):
        super().__init__(*args, pos=[0, 0], size=size, rotatable=False, **kwargs)
        # Each handle has a position, a fixed point for scaling and a cursor.
        for pos, center, cursor in [
            ([1, 1], [0, 0], Cursor.SizeFDiagCursor),
            ([0, 0], [1, 1], Cursor.SizeFDiagCursor),
            ([1, 0], [0, 1], Cursor.SizeBDiagCursor),
            ([0, 1], [1, 0], Cursor.SizeBDiagCursor),
            ([1, 0.5], [0, 0.5], Cursor.SizeHorCursor),
            ([0.5, 1], [0.5, 0], Cursor.SizeVerCursor),
            ([0, 0.5], [1, 0.5], Cursor.SizeHorCursor),
            ([0.5, 0], [0.5, 1], Cursor.SizeVerCursor),
        ]:
            self.addScaleHandle(pos, center).setCursor(cursor)
        self.setCursor(Cursor.OpenHandCursor)


class LineROI(DefaultLineROI):
    """Line with a width. The start handle is red and the end handle is black."""

    def __init__(self, pos1, pos2, width, *args, **kwargs):
        super().__init__(*args, pos1=pos1, pos2=pos2, width=width, **kwargs)
        ends = iter(
            [
                (LINE_ROI_HANDLE_COLOR_LEFT, LINE_ROI_HANDLE_HOOVER_COLOR_LEFT),
                (LINE_ROI_HANDLE_COLOR_RIGHT, LINE_ROI_HANDLE_HOOVER_COLOR_RIGHT),
            ]
        )
        for info in self.handles:
            handle = info["item"]
            if info["type"] == "sr":
                _set_pens(handle, *next(ends))
                handle.setCursor(Cursor.PointingHandCursor)
            else:
                _set_pens(handle, LINE_ROI_COLOR, LINE_ROI_HOOVER_COLOR)
                handle.setCursor(Cursor.SizeHorCursor)
        self.setCursor(Cursor.OpenHandCursor)

    def paint(self, painter, options, widget):
        r = QRectF(0, 0, self.state["size"][0], self.state["size"][1]).normalized()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(mkBrush(LINE_ROI_WIDTH_COLOR))
        painter.translate(r.left(), r.top())
        painter.scale(r.width(), r.height())
        painter.drawRect(0, 0, 1, 1)
        painter.setPen(mkPen(LINE_ROI_COLOR, width=4))
        painter.drawLine(QPointF(0, 0.5), QPointF(1, 0.5))

    def _offset(self, width, angle):
        """Return the offset from the start of the line to the corner of the ROI."""
        return Point(width / 2 * np.sin(angle), -width / 2 * np.cos(angle))

    def set_pos(self, start_coord, end_coord, width=None):
        width = self.get_width() if width is None else width
        pos1, pos2 = Point(*start_coord), Point(*end_coord)
        angle = (pos2 - pos1).angle(Point(1, 0), units="radians")
        self.setPos(pos1 + self._offset(width, angle), finish=False)
        self.setSize(Point((pos2 - pos1).length(), width), finish=False)
        self.setAngle(np.rad2deg(angle), finish=False)

    def get_pos(self):
        length, width = self.size().x(), self.size().y()
        angle = np.deg2rad(self.angle())
        pos1 = self.pos() - self._offset(width, angle)
        return pos1, pos1 + Point(length * np.cos(angle), length * np.sin(angle))

    def get_width(self):
        return self.size().y()
