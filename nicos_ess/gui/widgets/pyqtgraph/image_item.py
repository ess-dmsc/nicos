import numpy as np
from pyqtgraph import ImageItem

from nicos.guisupport.qt import QTimer, pyqtSignal


class CustomImageItem(ImageItem):
    hoverData = pyqtSignal(str)
    dragData = pyqtSignal(tuple)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptHoverEvents(True)
        self.hoverData.emit("")
        self.start_coord = None
        self.end_coord = None
        self.timer = QTimer()
        self.timer.setInterval(50)  # Update interval in milliseconds (e.g., 50ms)
        self.timer.timeout.connect(self.emitDragData)
        self.dragging = False
        self._defining_roi = False
        self._use_metric_length = False
        self._pix_to_mm_ratio = None
        self.last_clicked = None

    def set_define_roi_mode(self, state):
        self._defining_roi = state

    def set_metric_mode(self, state, pix_to_mm_ratio):
        self._pix_to_mm_ratio = pix_to_mm_ratio
        self._use_metric_length = state

    def _pix_to_mm(self, pix):
        return pix * self._pix_to_mm_ratio

    def get_pos(self, event):
        pos = event.pos()
        i, j = pos.x(), pos.y()
        i, j = (
            int(np.clip(i, 0, self.image.shape[0])),
            int(np.clip(j, 0, self.image.shape[1])),
        )
        return i, j

    def mousePressEvent(self, event):
        self.last_clicked = self.get_pos(event)
        if self._defining_roi:
            self.start_coord = self.get_pos(event)
            if self._use_metric_length:
                self.start_coord = (
                    self._pix_to_mm(self.start_coord[0]),
                    self._pix_to_mm(self.start_coord[1]),
                )
            self.dragging = True
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._defining_roi:
            if self.start_coord is not None and self.dragging:
                self.end_coord = self.get_pos(event)
                if self._use_metric_length:
                    self.end_coord = (
                        self._pix_to_mm(self.end_coord[0]),
                        self._pix_to_mm(self.end_coord[1]),
                    )
                if not self.timer.isActive():
                    self.timer.start()
                event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._defining_roi:
            if self.start_coord is not None and self.end_coord is not None:
                self.dragging = False
                self.emitDragData()
                self.timer.stop()
                self.start_coord = None
                self.end_coord = None
                event.accept()
        else:
            super().mouseReleaseEvent(event)

    def emitDragData(self):
        if self.start_coord is not None and self.end_coord is not None:
            self.dragData.emit((self.dragging, self.start_coord, self.end_coord))

    def hoverEvent(self, event):
        if event.isExit():
            self.hoverData.emit("")  # Clear any previous title
        else:
            i, j = self.get_pos(event)
            value = self.image[i, j]
            if self._use_metric_length:
                self.hoverData.emit(
                    f"Coordinates: ({self._pix_to_mm(i):.2f} mm, {self._pix_to_mm(j):.2f} mm), Value: {value:.2f}"
                )
            else:
                self.hoverData.emit(f"Coordinates: ({i}, {j}), Value: {value:.2f}")
