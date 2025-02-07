import matplotlib.pyplot as plt
import numpy as np
import pyqtgraph as pg
from pyqtgraph import AxisItem, GraphicsView, HistogramLUTItem, mkPen

from nicos.guisupport.qt import QAction, QSizePolicy


class HistogramItem(HistogramLUTItem):
    def __init__(
        self,
        image=None,
        fillHistogram=True,
        levelMode="mono",
        gradientPosition="right",
        orientation="vertical",
        color=(100, 100, 200),
    ):
        HistogramLUTItem.__init__(
            self,
            image=image,
            fillHistogram=fillHistogram,
            levelMode=levelMode,
            gradientPosition=gradientPosition,
            orientation=orientation,
        )
        if orientation == "horizontal":
            self.layout.removeItem(self.axis)
            self.layout.removeItem(self.vb)
            self.layout.removeItem(self.gradient)
            self.axis = AxisItem(
                "bottom", linkView=self.vb, maxTickLength=-10, parent=self
            )
            self.axis_2 = AxisItem(
                "left", linkView=self.vb, maxTickLength=-30, parent=self
            )
            self.layout.addItem(self.axis_2, 0, 0)
            self.layout.addItem(self.vb, 0, 1)
            self.layout.addItem(self.axis, 1, 1)
            self.layout.addItem(self.gradient, 2, 1)

        for act in self.gradient.menu.actions():
            try:
                if act.name in ["spectrum", "cyclic"]:
                    self.gradient.menu.removeAction(act)
            except AttributeError:
                pass

        self.gradient.hsvAction.setCheckable(False)
        self.gradient.hsvAction.triggered.disconnect(self.gradient._setColorModeToHSV)
        self.gradient.menu.removeAction(self.gradient.hsvAction)
        self.gradient.menu.removeAction(self.gradient.rgbAction)

        self.add_colormap_to_menu("bwr", self.create_matplotlib_colormap("bwr"))

        self.fillHistogram(fillHistogram, color=color)
        self.vb.setAutoVisible(y=True)

        self.vb.setMaximumHeight(1000)

    def add_colormap_to_menu(self, name, colormap):
        action = QAction(name, self.gradient)
        action.triggered.connect(lambda: self.gradient.setColorMap(colormap))
        self.gradient.menu.addAction(action)

    def create_matplotlib_colormap(self, cmap_name):
        cmap = plt.get_cmap(cmap_name)
        pos = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        color = np.array([cmap(p)[:3] for p in pos])
        color = (color * 255).astype(np.uint8)
        return pg.ColorMap(pos, color)

    def imageChanged(self, autoLevel=False, autoRange=False, bins=None):
        if self.imageItem() is None:
            return

        if self.levelMode != "mono":
            self.log.error("Only mono images are supported")
            return

        for plot in self.plots[1:]:
            plot.setVisible(False)
        self.plots[0].setVisible(True)
        # plot one histogram for all image data
        if bins:
            histogram = self.imageItem().getHistogram(bins)
        else:
            histogram = self.imageItem().getHistogram()
        if histogram[0] is None:
            return
        self.plot.setData(*histogram)
        if autoLevel:
            mn = histogram[0][0]
            mx = histogram[0][-1]
            self.region.setRegion([mn, mx])
        else:
            mn, mx = self.imageItem().levels
            self.region.setRegion([mn, mx])

    def gradientChanged(self):
        super().gradientChanged()
        for tick in self.gradient.ticks.keys():
            tick.pen = mkPen(0, 0, 0, 130)
            tick.hoverPen = mkPen(0, 0, 0, 255)
            tick.currentPen = tick.pen


class HistogramWidget(GraphicsView):
    def __init__(self, parent=None, remove_regions=False, *args, **kargs):
        background = kargs.pop("background", "default")
        GraphicsView.__init__(self, parent, useOpenGL=False, background=background)
        self.item = HistogramItem(*args, **kargs)
        self.setCentralItem(self.item)

        self.orientation = kargs.get("orientation", "vertical")
        if self.orientation == "vertical":
            self.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Expanding,
            )
            self.setMinimumWidth(95)
        else:
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )
            self.setMinimumHeight(95)

        if remove_regions:
            self.region.setVisible(False)
            self.item.plot.hide()
            for region in self.regions:
                self.vb.removeItem(region)
                del region
            self.vb.removeItem(self.gradient)

    def __getattr__(self, attr):
        return getattr(self.item, attr)
