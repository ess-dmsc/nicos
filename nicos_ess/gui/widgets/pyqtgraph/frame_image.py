"""The image of a plot together with the data that measurements on it need."""

import numpy as np

from nicos.guisupport.qt import QObject, pyqtSignal
from nicos_ess.gui.widgets.pyqtgraph.coords import CoordinateGrid
from nicos_ess.gui.widgets.pyqtgraph.frame_format import keeps_proportions
from nicos_ess.gui.widgets.pyqtgraph.image_layer import ImageLayer


class FrameImage(QObject):
    """The image of *plot* with its shown values, axes and ``counts``.

    The values are indexed [y, x]. ``grid_changed`` is emitted with the new
    `CoordinateGrid` when an image comes on other axes.
    """

    image_changed = pyqtSignal(object)
    grid_changed = pyqtSignal(object)

    def __init__(self, plot):
        super().__init__()
        self.layer = ImageLayer(plot)
        self.grid = self.data = None
        # This holds the x and y `frame_views.Axis` of the image.
        self._axes = ()

    def set_image(self, values, x, y, x_edges, y_edges, counts=False):
        self.data, self.counts = np.asarray(values, dtype=float), counts
        self._axes = (x, y)
        grid = CoordinateGrid(x_edges, y_edges)
        if not grid.same_as(self.grid):
            self.grid = grid
            self.grid_changed.emit(grid)
        self.layer.set_image(self.data, x_edges, y_edges)
        self.image_changed.emit(self.data)

    def axis(self, name):
        """Return the `Axis` "x" or "y" of the shown image."""
        return self._axes[name == "y"] if self._axes else None

    def axis_label(self, name):
        return self._axes[name == "y"].dim if self._axes else ""

    def axis_unit(self, name):
        return self._axes[name == "y"].unit if self._axes else ""

    def same_space(self):
        """Return whether a distance across the image has a meaning.

        It has none for Q against energy, or across tubes and the pixels
        along them.
        """
        return bool(self._axes) and keeps_proportions(*self._axes)
