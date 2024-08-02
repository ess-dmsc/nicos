# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2023 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

import numpy as np
import pyqtgraph as pg
from pyqtgraph import Point, mkBrush, mkPen
from pyqtgraph.graphicsItems.ROI import ROI, LineROI as DefaultLineROI

from nicos.guisupport.qt import QPainter, QPointF, QRectF, Qt, QCursor


CROSS_COLOR = (255, 165, 0, 150)
CROSS_HOOVER_COLOR = (255, 165, 0, 255)
ROI_COLOR = (7, 188, 230, 180)
ROI_HOOVER_COLOR = (7, 188, 230, 255)
ROI_HANDLE_COLOR = (7, 188, 230, 180)
ROI_HANDLE_HOOVER_COLOR = (7, 188, 230, 255)
LINE_ROI_WIDTH_COLOR = (166, 0, 255, 100)
LINE_ROI_COLOR = (166, 0, 255, 180)
LINE_ROI_HOOVER_COLOR = (166, 0, 255, 255)
LINE_ROI_HANDLE_COLOR_LEFT = (255, 0, 0, 180)
LINE_ROI_HANDLE_HOOVER_COLOR_LEFT = (255, 0, 0, 255)
LINE_ROI_HANDLE_COLOR_RIGHT = (0, 0, 0, 180)
LINE_ROI_HANDLE_HOOVER_COLOR_RIGHT = (0, 0, 0, 255)


class PlotROI(ROI):
    def __init__(self, size, *args, **kwargs):
        ROI.__init__(
            self,
            pos=[0, 0],
            size=size,
            rotatable=False,
            *args,
            **kwargs,
        )
        self._setup_handles()

    def _setup_handles(self):
        positions = [
            ([1, 1], [0, 0]),
            ([0, 0], [1, 1]),
            ([1, 0], [0, 1]),
            ([0, 1], [1, 0]),
            ([1, 0.5], [0, 0.5]),
            ([0.5, 1], [0.5, 0]),
            ([0, 0.5], [1, 0.5]),
            ([0.5, 0], [0.5, 1]),
        ]
        cursors = [
            Qt.CursorShape.SizeFDiagCursor,
            Qt.CursorShape.SizeFDiagCursor,
            Qt.CursorShape.SizeBDiagCursor,
            Qt.CursorShape.SizeBDiagCursor,
            Qt.CursorShape.SizeHorCursor,
            Qt.CursorShape.SizeVerCursor,
            Qt.CursorShape.SizeHorCursor,
            Qt.CursorShape.SizeVerCursor,
        ]
        for (pos, center), cursor in zip(positions, cursors):
            handle = self.addScaleHandle(pos, center)
            handle.setCursor(cursor)
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))


class LineROI(DefaultLineROI):
    def __init__(self, pos1, pos2, width, *args, **kwargs):
        DefaultLineROI.__init__(
            self,
            pos1=pos1,
            pos2=pos2,
            width=width,
            *args,
            **kwargs,
        )
        self._setup_handles()

    def paint(self, pen, options, widget):
        r = QRectF(0, 0, self.state["size"][0], self.state["size"][1]).normalized()
        pen.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen.setPen(Qt.PenStyle.NoPen)
        pen.setBrush(mkBrush(LINE_ROI_WIDTH_COLOR))
        pen.translate(r.left(), r.top())
        pen.scale(r.width(), r.height())
        pen.drawRect(0, 0, 1, 1)

        pen.setPen(mkPen(LINE_ROI_COLOR, width=4))
        point_1 = QPointF(0, 0.5)
        point_2 = QPointF(1, 0.5)
        pen.drawLine(point_1, point_2)

    def _setup_handles(self):
        first_flag = False
        for handle_info in self.handles:
            handle = handle_info["item"]
            h_type = handle_info["type"]
            if h_type == "sr":
                handle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                if not first_flag:
                    first_flag = True
                    handle.pen = mkPen(LINE_ROI_HANDLE_COLOR_LEFT, width=2)
                    handle.currentPen = handle.pen
                    handle.hoverPen = mkPen(LINE_ROI_HANDLE_HOOVER_COLOR_LEFT, width=2)
                else:
                    handle.pen = mkPen(LINE_ROI_HANDLE_COLOR_RIGHT, width=2)
                    handle.currentPen = handle.pen
                    handle.hoverPen = mkPen(LINE_ROI_HANDLE_HOOVER_COLOR_RIGHT, width=2)
            else:
                handle.pen = mkPen(LINE_ROI_COLOR, width=2)
                handle.currentPen = handle.pen
                handle.hoverPen = mkPen(LINE_ROI_HOOVER_COLOR, width=2)
                handle.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))

        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

    def set_pos(self, start_coord, end_coord, width=None):
        if width is None:
            width = self.get_width()
        pos1 = Point(*start_coord)
        pos2 = Point(*end_coord)
        distance = pos2 - pos1
        length = distance.length()
        angle = distance.angle(Point(1, 0), units="radians")
        center = Point(width / 2.0 * np.sin(angle), -width / 2.0 * np.cos(angle))
        pos1 = pos1 + center

        self.setPos(pos1)
        self.setSize(Point(length, width))
        self.setAngle(np.rad2deg(angle))

    def get_pos(self):
        pos = self.pos()
        size = self.size()
        angle = np.deg2rad(self.angle())

        length, width = size.x(), size.y()

        center = Point(width / 2.0 * np.sin(angle), -width / 2.0 * np.cos(angle))

        original_pos1 = pos - center

        dx = length * np.cos(angle)
        dy = length * np.sin(angle)
        pos2 = Point(original_pos1.x() + dx, original_pos1.y() + dy)

        return original_pos1, pos2

    def get_width(self):
        return self.size().y()


class CrossROI:
    def __init__(self):
        self.first_show = True
        pen = mkPen(CROSS_COLOR, width=3)
        hover_pen = mkPen(CROSS_HOOVER_COLOR, width=3)
        self.vertical_line = pg.InfiniteLine(
            pos=10,
            angle=90,
            movable=True,
            pen=pen,
            hoverPen=hover_pen,
        )
        self.horizontal_line = pg.InfiniteLine(
            pos=10, angle=0, movable=True, pen=pen, hoverPen=hover_pen
        )
        self.vertical_line.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        self.horizontal_line.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        self.vertical_line.setZValue(100)
        self.horizontal_line.setZValue(100)
