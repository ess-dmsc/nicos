"""Slim rows under a plot choose the bins of the dims that are not drawn.

Each row has the name of a dim, a slider with two handles over its bins and
the chosen window as text. The plot sums or averages over the window.
"""

from dataclasses import dataclass

import pyqtgraph as pg

from nicos.guisupport.qt import QColor, QFontMetricsF, QPainter, QRectF, Qt, pyqtSignal
from nicos_ess.gui.widgets.pyqtgraph.theme import (
    ACCENT,
    MUTED,
    SLATE,
    TICK_SCALE,
    scaled_font,
)

TRACK_COLOR = "#d9d9d9"
WINDOW_COLOR = QColor(ACCENT)
WINDOW_COLOR.setAlpha(120)
HANDLE = 4  # The handles are this many px wide, outside the window.
GRAB = 6  # A press this close to the window in px grabs a handle.
MIN_WINDOW = 4  # A window narrower than this many px is drawn this wide.
GAP = 6  # This gap in px separates the name, the slider and the text.
TIP = (
    "Drag a handle to move one end, or drag the window to move all of it.\n"
    "Click the track to move the window there.\n"
    "The wheel, or Shift + wheel over the plot, moves the window by one bin.\n"
    "A double-click chooses all bins."
)


@dataclass
class Row:
    """A row stands for a dim with *size* bins and the window (start, stop) of
    bins in the dim.
    """

    dim: str
    size: int
    window: tuple
    text: str


class RangeSliders(pg.GraphicsWidget):
    """This widget has a row with a range slider for each dim that the plot
    does not draw.

    ``moved`` sends the dim and its new window when the user moves a slider.
    """

    moved = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        self.font = scaled_font(TICK_SCALE)
        self.metrics = QFontMetricsF(self.font)
        self.row_height = round(self.metrics.height()) + 1
        self.rows = None  # The first set_rows sets the height.
        # The room for the text only grows, so the slider does not jitter.
        self.text_room = 0.0
        # During a drag this holds (dim, part, offset in bins, width).
        self.grab = None
        # The track keeps its ends during a drag so the handle stays under the pointer.
        self.held_track = None
        self.setAcceptHoverEvents(True)
        self.set_rows([])

    def set_rows(self, rows):
        if self.rows is None or [r.dim for r in rows] != [r.dim for r in self.rows]:
            self.text_room = 0.0
            height = self.row_height * len(rows)
            self.setMinimumHeight(height)
            self.setMaximumHeight(height)
            self.setVisible(bool(rows))
        self.rows = rows
        # One more digit fits, so the room rarely grows while a window moves.
        for row in rows:
            width = self.metrics.horizontalAdvance(row.text + "0")
            self.text_room = max(self.text_room, width)
        self.update()

    def _name_room(self):
        widest = max(self.metrics.horizontalAdvance(r.dim) for r in self.rows)
        return min(widest, self.width() * 0.3)

    def _track(self):
        """Return the left and right end of the tracks in px."""
        if self.held_track:
            return self.held_track
        left = GAP + self._name_room() + GAP + HANDLE
        right = self.width() - GAP - self.text_room - GAP - HANDLE
        return left, max(right, left + 1)

    def bin_x(self, row, b):
        """Return the x position in px of the left edge of bin *b* in *row*."""
        left, right = self._track()
        return left + (right - left) * b / row.size

    def _window_px(self, row):
        x0, x1 = (self.bin_x(row, b) for b in row.window)
        if x1 - x0 < MIN_WINDOW:
            mid = (x0 + x1) / 2
            x0, x1 = mid - MIN_WINDOW / 2, mid + MIN_WINDOW / 2
        return x0, x1

    def _bin_at(self, row, x):
        left, right = self._track()
        return (x - left) / (right - left) * row.size

    def _row(self, dim):
        return next((r for r in self.rows if r.dim == dim), None)

    def _at(self, pos):
        """Return the row under *pos* and the part of the slider there.

        The part is None beside the slider, and the row is None below the rows.
        """
        index = int(pos.y() // self.row_height)
        if not 0 <= index < len(self.rows) or not self.rows[index].size:
            return None, None
        row, x = self.rows[index], pos.x()
        x0, x1 = self._window_px(row)
        left, right = self._track()
        if x0 - GRAB <= x < x0:
            return row, "low"
        if x1 < x <= x1 + GRAB:
            return row, "high"
        if x0 <= x <= x1:
            return row, "middle"
        return row, "track" if left - HANDLE <= x <= right + HANDLE else None

    def _move(self, row, start, stop):
        if (start, stop) != tuple(row.window):
            self.moved.emit(row.dim, (start, stop))

    def paint(self, painter, *_args):
        if not self.rows:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font)
        left, right = self._track()
        name_room, h = self._name_room(), self.row_height
        align = Qt.AlignmentFlag.AlignVCenter
        for i, row in enumerate(self.rows):
            top, mid = i * h, i * h + h / 2
            painter.setPen(QColor(MUTED))
            name = self.metrics.elidedText(
                row.dim, Qt.TextElideMode.ElideRight, name_room
            )
            painter.drawText(QRectF(GAP, top, name_room, h), align, name)
            painter.setPen(QColor("#222"))
            text_box = QRectF(right + HANDLE + GAP, top, self.text_room, h)
            painter.drawText(text_box, align, row.text)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(TRACK_COLOR))
            painter.drawRoundedRect(QRectF(left, mid - 2, right - left, 4), 2, 2)
            if not row.size:
                continue
            x0, x1 = self._window_px(row)
            painter.setBrush(WINDOW_COLOR)
            painter.drawRect(QRectF(x0, mid - 4, x1 - x0, 8))
            grabbed = self.grab and self.grab[0] == row.dim and self.grab[1]
            for part, x in (("low", x0 - HANDLE), ("high", x1)):
                on = grabbed in (part, "middle")
                painter.setBrush(QColor(ACCENT if on else SLATE))
                painter.drawRoundedRect(QRectF(x, mid - 6, HANDLE, 12), 1.5, 1.5)

    def hoverEvent(self, ev):
        if ev.isExit():
            self.unsetCursor()
            return
        row, part = self._at(ev.pos())
        if row is None:
            self.unsetCursor()
            return
        ev.acceptDrags(Qt.MouseButton.LeftButton)
        ev.acceptClicks(Qt.MouseButton.LeftButton)
        shapes = {
            "low": Qt.CursorShape.SizeHorCursor,
            "high": Qt.CursorShape.SizeHorCursor,
            "middle": Qt.CursorShape.OpenHandCursor,
            "track": Qt.CursorShape.PointingHandCursor,
        }
        if part is None:
            self.unsetCursor()
        else:
            self.setCursor(shapes[part])
        start, stop = row.window
        bins = f"bin {start}" if stop - start == 1 else f"bins {start}–{stop - 1}"
        self.setToolTip(f"{row.dim} {row.text}, {bins} of {row.size}\n{TIP}")

    def mouseClickEvent(self, ev):
        row, part = self._at(ev.pos())
        if row is None or ev.button() != Qt.MouseButton.LeftButton:
            ev.ignore()
            return
        ev.accept()
        if ev.double():
            self._move(row, 0, row.size)
        elif part == "track":
            self._center(row, self._bin_at(row, ev.pos().x()))

    def _center(self, row, at):
        start, stop = row.window
        width = stop - start
        start = max(0, min(round(at - width / 2), row.size - width))
        self._move(row, start, start + width)

    def mouseDragEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            ev.ignore()
            return
        if ev.isStart() and not self._grab_at(ev.buttonDownPos()):
            ev.ignore()
            return
        if self.grab is None:
            ev.ignore()
            return
        ev.accept()
        dim, part, offset, width = self.grab
        if (row := self._row(dim)) is not None:
            at = round(self._bin_at(row, ev.pos().x()) - offset)
            self._drag_to(row, part, at, width)
        if ev.isFinish():
            self.grab = self.held_track = None
            self.update()

    def _grab_at(self, pos):
        """Grab the part of a slider at *pos* and return False if there is none.

        A click on the track first centres the window there and then grabs it
        in the middle.
        """
        row, part = self._at(pos)
        if part is None:
            return False
        at = self._bin_at(row, pos.x())
        if part == "track":
            self._center(row, at)
            row, part = self._row(row.dim), "middle"
        start, stop = row.window
        offset = at - (stop if part == "high" else start)
        self.grab = (row.dim, part, offset, stop - start)
        self.held_track = self._track()
        return True

    def _drag_to(self, row, part, at, width):
        """Move the grabbed *part* of the slider in *row* to the bin *at*."""
        start, stop = row.window
        if part == "low":
            self._move(row, max(0, min(at, stop - 1)), stop)
        elif part == "high":
            self._move(row, start, max(start + 1, min(at, row.size)))
        else:
            start = max(0, min(at, row.size - width))
            self._move(row, start, start + width)

    def wheelEvent(self, ev):
        row, _part = self._at(ev.pos())
        if row is None:
            ev.ignore()
            return
        ev.accept()
        start, stop = row.window
        width = stop - start
        start = max(0, min(start + (1 if ev.delta() > 0 else -1), row.size - width))
        self._move(row, start, start + width)
