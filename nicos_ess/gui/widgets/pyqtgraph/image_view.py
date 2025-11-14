import numpy as np
import pyqtgraph as pg
from pyqtgraph import ColorMap, GraphicsView, ImageItem, PlotWidget, mkPen

from nicos.guisupport.qt import (
    QAction,
    QApplication,
    QCursor,
    QLabel,
    QSplitter,
    Qt,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
    pyqtSlot,
)
from nicos.utils.loggers import NicosLogger
from nicos_ess.gui.widgets.pyqtgraph.histogram import HistogramWidget
from nicos_ess.gui.widgets.pyqtgraph.image_item import CustomImageItem
from nicos_ess.gui.widgets.pyqtgraph.image_view_controller import ImageViewController
from nicos_ess.gui.widgets.pyqtgraph.roi import (
    CROSS_COLOR,
    CROSS_HOOVER_COLOR,
    LINE_ROI_HANDLE_HOOVER_COLOR_LEFT,
    LINE_ROI_HANDLE_HOOVER_COLOR_RIGHT,
    LINE_ROI_HOOVER_COLOR,
    ROI_COLOR,
    ROI_HANDLE_COLOR,
    ROI_HANDLE_HOOVER_COLOR,
    ROI_HOOVER_COLOR,
    CrossROI,
    LineROI,
    PlotROI,
)
from nicos_ess.gui.widgets.pyqtgraph.stats_dialog import StatisticsDialog

pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")
pg.setConfigOptions(antialias=True)

HORI_SPLITTER_SIZES_1 = [100, 500]
VERT_SPLITTER_SIZES_1 = [100, 500, 100]
VERT_SPLITTER_SIZES_2 = [100, 500, 100]
VERT_SPLITTER_SIZES_3 = [50, 1000]


class CustomAxisItem(pg.AxisItem):
    def __init__(self, orientation, **kwargs):
        super().__init__(orientation, **kwargs)
        self.labels_array = None

    def setLabelsArray(self, arr):
        self.labels_array = np.asarray(arr, dtype=float)
        self.update()

    def tickStrings(self, values, scale, spacing):
        if self.labels_array is None:
            return super().tickStrings(values, scale, spacing)

        strings = []
        for val in values:
            idx = np.searchsorted(self.labels_array, val)
            if idx == 0:
                if val < np.min(self.labels_array):
                    strings.append("")
                else:
                    strings.append(f"{self.labels_array[0]:.4g}")
                continue
            elif idx >= len(self.labels_array):
                if val > np.max(self.labels_array):
                    strings.append("")
                else:
                    strings.append(f"{self.labels_array[-1]:.4g}")
                continue
            else:
                if abs(val - self.labels_array[idx - 1]) < abs(
                    val - self.labels_array[idx]
                ):
                    label_val = self.labels_array[idx - 1]
                else:
                    label_val = self.labels_array[idx]
            strings.append(f"{label_val:.4g}")
        return strings


class ImageView(QWidget):
    sigTimeChanged = pyqtSignal(object, object)
    sigProcessingChanged = pyqtSignal(object)
    clicked = pyqtSignal(str)

    def __init__(
        self,
        parent=None,
        name="",
        histogram_orientation="horizontal",
        use_internal_image_view_controller=False,
        invert_y=True,
        *args,
    ):
        QWidget.__init__(self, parent, *args)
        self.parent = parent
        self.name = name
        self.histogram_orientation = histogram_orientation
        self._internal_image_view_controller = use_internal_image_view_controller
        self._invert_y = invert_y

        self.log = NicosLogger("ImageView")
        self.log.parent = parent.log.parent

        stats = ("mean", "std", "max", "min")
        for attr in ("roi", "v", "h"):
            for stat in stats:
                setattr(self, f"{attr}_{stat}", 0)

        self.saved_roi_state = None
        self.saved_line_roi_state = None
        self.log_mode = False
        self.saved_cm = None
        self.autolevel_complete = False
        self.image = None
        self.select_pixels = False
        self.selected_pixels = []
        self._use_metric_length = False
        self._line_roi_drag_active = False
        self._roi_drag_active = False
        self.autolevel_on_update = False
        self.axes = {"t": None, "x": 0, "y": 1, "c": None}
        self._axis_world_extents = None  # (x_min, x_max, y_min, y_max)

        self.initialize_ui()
        self.build_image_controller_tab()
        self.build_main_image_item()
        self.build_rois()
        self.build_histograms()
        self.build_plots()
        self.build_ui()

        self.setup_connections()

        self.statisticsAction = QAction("Calculate Statistics", self)
        self.statisticsAction.triggered.connect(self.calculate_statistics)
        self.view.menu.addAction(self.statisticsAction)

        self.addSelectedPixelAction = QAction("Add Selected Pixel", self)
        self.addSelectedPixelAction.triggered.connect(self.add_selected_pixel)
        self.view.menu.addAction(self.addSelectedPixelAction)

        self.aspectLockedAction = QAction("Aspect Locked", self)
        self.aspectLockedAction.setCheckable(True)
        self.aspectLockedAction.setChecked(True)
        self.aspectLockedAction.triggered.connect(self.set_aspect_locked)
        self.view.menu.addAction(self.aspectLockedAction)

        self.autoLevelsAction = QAction("Auto Levels Now", self)
        self.autoLevelsAction.triggered.connect(lambda: self.autolevel_now())
        self.view.menu.addAction(self.autoLevelsAction)

        self.logScaleAction = QAction("Logarithmic colormap", self)
        self.logScaleAction.setCheckable(True)
        self.logScaleAction.setChecked(False)
        self.logScaleAction.toggled.connect(self.toggle_log_mode)
        self.view.menu.addAction(self.logScaleAction)

        for child in self.view.menu.actions():
            if child.text() == "View All":
                child.triggered.connect(self.set_auto_scale_axis)

    def set_auto_scale_axis(self):
        self.view.enableAutoRange(x=True, y=True)

    def set_aspect_locked(self, state=None):
        if state is None:
            state = self.aspectLockedAction.isChecked()
        self.image_plot.setAspectLocked(bool(state))

    def set_autolevel_on_update(self, enabled: bool):
        self.autolevel_on_update = bool(enabled)

    def autolevel_now(self):
        # recompute and apply levels immediately
        self.autolevel_complete = False
        self.update_image(
            self.image_item.image if self.image_item.image is not None else None
        )

    def calculate_statistics(self):
        image_stats = {
            stat: getattr(self.image_item.image, stat)()
            for stat in ("mean", "std", "min", "max")
        }

        roi_stats = (
            {
                f"ROI {stat}": getattr(self, f"roi_{stat}")
                for stat in ("mean", "std", "min", "max")
            }
            if self.roi.isVisible()
            else {}
        )

        vert_stats = (
            {
                f"Vertical {stat}": getattr(self, f"v_{stat}")
                for stat in ("mean", "std", "min", "max")
            }
            if self.crosshair_roi.vertical_line.isVisible()
            else {}
        )

        hori_stats = (
            {
                f"Horizontal {stat}": getattr(self, f"h_{stat}")
                for stat in ("mean", "std", "min", "max")
            }
            if self.crosshair_roi.horizontal_line.isVisible()
            else {}
        )

        crosshair_stats = {**vert_stats, **hori_stats}

        stats_dialog = StatisticsDialog(image_stats, roi_stats, crosshair_stats)
        stats_dialog.exec_()

    def initialize_ui(self):
        self.ui = QVBoxLayout(self)
        self.hover_label = QLabel(self)
        self.graphics_view = GraphicsView()
        self.scene = self.graphics_view.scene()
        self.image_plot = pg.PlotItem()
        if self._invert_y:
            self.image_plot.invertY()
        self.image_plot.setAspectLocked(True)
        self.view = self.image_plot.vb
        self.graphics_view.setCentralItem(self.image_plot)

    def build_image_controller_tab(self):
        self.image_view_controller = ImageViewController(self)

    def build_main_image_item(self):
        self.image_item = CustomImageItem()
        self.image_item.setAutoDownsample(True)
        self.view.addItem(self.image_item)

    def build_rois(self):
        self.crosshair_roi = CrossROI()
        self.crosshair_roi.vertical_line.hide()
        self.crosshair_roi.horizontal_line.hide()
        self.view.addItem(self.crosshair_roi.vertical_line, ignoreBounds=True)
        self.view.addItem(self.crosshair_roi.horizontal_line, ignoreBounds=True)

        self.roi = PlotROI(
            0,
            pen=mkPen(ROI_COLOR, width=4),
            hoverPen=mkPen(ROI_HOOVER_COLOR, width=4),
        )
        self.roi.hide()
        for handle in self.roi.handles:
            handle["item"].pen = mkPen(ROI_HANDLE_COLOR, width=2)
            handle["item"].hoverPen = mkPen(ROI_HANDLE_HOOVER_COLOR, width=2)
            handle["item"].currentPen = mkPen(ROI_HANDLE_COLOR, width=2)
        self.roi.setZValue(20)
        self.view.addItem(self.roi)
        self.saved_roi_state = self.roi.saveState()

        self.line_roi = LineROI(
            [10, 10],
            [50, 10],
            1,
            pen=mkPen(ROI_COLOR, width=4),
            hoverPen=mkPen(ROI_HOOVER_COLOR, width=4),
        )
        self.line_roi.hide()
        self.saved_line_roi_state = self.line_roi.saveState()
        self.view.addItem(self.line_roi)

    def build_histograms(self):
        self.settings_histogram = HistogramWidget(
            orientation=self.histogram_orientation
        )
        self.settings_histogram.gradient.loadPreset("viridis")
        self.settings_histogram.item.log = self.log
        self.settings_histogram.item.setImageItem(self.image_item)

        for act in self.settings_histogram.item.gradient.menu.actions():
            act.triggered.connect(self._colormap_changed_from_menu)

        self.histogram_image_item = ImageItem()
        self.roi_histogram = HistogramWidget(
            orientation="horizontal",
            remove_regions=True,
            color=ROI_COLOR,
        )
        self.roi_histogram.item.log = self.log
        self.roi_histogram.item.setImageItem(self.histogram_image_item)

    def build_plots(self):
        self.left_plot = PlotWidget()
        self.bottom_plot = PlotWidget()
        self.line_plot = PlotWidget()
        self.left_plot.setYLink(self.view)
        self.bottom_plot.setXLink(self.view)

        self.full_vert_trace = self.left_plot.plot(pen=mkPen("k", width=0.5))
        self.left_crosshair_roi_hline = pg.InfiniteLine(
            pos=10,
            angle=0,
            movable=False,
            pen=mkPen(CROSS_COLOR, width=3),
            hoverPen=mkPen(CROSS_HOOVER_COLOR, width=3),
        )
        self.left_crosshair_roi = self.left_plot.plot(
            pen=mkPen(CROSS_HOOVER_COLOR, width=1)
        )
        self.left_roi_trace = self.left_plot.plot(pen=mkPen(ROI_HOOVER_COLOR, width=1))
        self.left_crosshair_roi_hline.setVisible(False)
        self.left_plot.addItem(self.left_crosshair_roi_hline)
        if self._invert_y:
            self.left_plot.invertY()
        self.left_plot.showGrid(x=True, y=True, alpha=0.2)
        self.left_plot.setLabel("left", "Pixels")

        self.full_hori_trace = self.bottom_plot.plot(pen=mkPen("k", width=0.5))
        self.bottom_crosshair_roi_vline = pg.InfiniteLine(
            pos=10,
            angle=90,
            movable=False,
            pen=mkPen(CROSS_COLOR, width=3),
            hoverPen=mkPen(CROSS_HOOVER_COLOR, width=3),
        )
        self.bottom_crosshair_roi = self.bottom_plot.plot(
            pen=mkPen(CROSS_HOOVER_COLOR, width=1)
        )
        self.bottom_roi_trace = self.bottom_plot.plot(
            pen=mkPen(ROI_HOOVER_COLOR, width=1)
        )
        self.bottom_crosshair_roi_vline.setVisible(False)
        self.bottom_plot.addItem(self.bottom_crosshair_roi_vline)
        self.bottom_plot.showGrid(x=True, y=True, alpha=0.2)
        self.bottom_plot.setLabel("bottom", "Pixels")

        self.line_roi_trace = self.line_plot.plot(
            pen=mkPen(LINE_ROI_HOOVER_COLOR, width=1)
        )
        self.line_roi_trace_left = pg.ScatterPlotItem(
            pen=mkPen(LINE_ROI_HANDLE_HOOVER_COLOR_LEFT), brush=None
        )
        self.line_roi_trace_right = pg.ScatterPlotItem(
            pen=mkPen(LINE_ROI_HANDLE_HOOVER_COLOR_RIGHT), brush=None
        )
        self.line_plot.addItem(self.line_roi_trace_left)
        self.line_plot.addItem(self.line_roi_trace_right)
        self.line_plot.showGrid(x=True, y=True, alpha=0.2)
        self.line_plot.setLabel("bottom", "Pixels")

    def build_ui(self):
        self.splitter_vert_1 = QSplitter(Qt.Orientation.Vertical)
        self.splitter_vert_1.addWidget(self.roi_histogram)
        self.splitter_vert_1.addWidget(self.left_plot)
        # self.splitter_vert_1.addWidget(self.roi_info_frame)
        self.splitter_vert_1.addWidget(self.line_plot)

        self.splitter_vert_2 = QSplitter(Qt.Orientation.Vertical)
        if self.histogram_orientation == "horizontal":
            self.splitter_vert_2.addWidget(self.settings_histogram)
        self.splitter_vert_2.addWidget(self.graphics_view)
        self.splitter_vert_2.addWidget(self.bottom_plot)

        self.splitter_hori_1 = QSplitter(Qt.Orientation.Horizontal)
        self.splitter_hori_1.addWidget(self.splitter_vert_1)
        self.splitter_hori_1.addWidget(self.splitter_vert_2)
        if self.histogram_orientation == "vertical":
            self.splitter_hori_1.addWidget(self.settings_histogram)
        if self._internal_image_view_controller:
            self.splitter_hori_1.addWidget(self.image_view_controller)

        self.splitter_vert_3 = QSplitter(Qt.Orientation.Vertical)
        self.splitter_vert_3.addWidget(self.splitter_hori_1)

        self.splitter_hori_1.setSizes(HORI_SPLITTER_SIZES_1)
        self.splitter_vert_1.setSizes(VERT_SPLITTER_SIZES_1)
        self.splitter_vert_2.setSizes(VERT_SPLITTER_SIZES_2)
        self.splitter_vert_3.setSizes(VERT_SPLITTER_SIZES_3)

        self.ui.addWidget(self.splitter_vert_3)
        self.ui.addWidget(self.hover_label)

        self.setLayout(self.ui)

    def setup_connections(self):
        self.image_item.sigImageChanged.connect(self.update_trace)
        self.image_item.hoverData.connect(self.set_hover_title)
        self.settings_histogram.sigLevelsChanged.connect(self.update_hist_levels_text)

        self.splitter_vert_1.splitterMoved.connect(
            lambda x: self.splitter_moved(self.splitter_vert_1)
        )
        self.splitter_vert_2.splitterMoved.connect(
            lambda x: self.splitter_moved(self.splitter_vert_2)
        )

    def add_image_axes(self):
        self.custom_bottom_axis = CustomAxisItem(orientation="bottom")
        self.custom_left_axis = CustomAxisItem(orientation="left")
        self.image_plot.setAxisItems(
            {"bottom": self.custom_bottom_axis, "left": self.custom_left_axis}
        )
        self.image_plot.showGrid(x=True, y=True, alpha=0.2)

    def set_crosshair_roi_visibility(self, visible, ignore_connections=False):
        self.roi_crosshair_active = visible
        self.left_crosshair_roi.setVisible(visible)
        self.bottom_crosshair_roi.setVisible(visible)

        for item in [
            self.left_crosshair_roi,
            self.bottom_crosshair_roi,
            self.crosshair_roi.vertical_line,
            self.crosshair_roi.horizontal_line,
            self.left_crosshair_roi_hline,
            self.bottom_crosshair_roi_vline,
        ]:
            item.setVisible(visible)

        if ignore_connections:
            return

        if visible:
            if self.crosshair_roi.first_show:
                view_center = self.view.viewRect().center()
                self.crosshair_roi.vertical_line.setPos(view_center.x())
                self.crosshair_roi.horizontal_line.setPos(view_center.y())
                self.crosshair_roi.first_show = False

            self.image_item.sigImageChanged.connect(self.crosshair_roi_changed)
            self.crosshair_roi.vertical_line.sigPositionChanged.connect(
                self.crosshair_roi_changed
            )
            self.crosshair_roi.horizontal_line.sigPositionChanged.connect(
                self.crosshair_roi_changed
            )
        else:
            self.image_item.sigImageChanged.disconnect(self.crosshair_roi_changed)
            self.crosshair_roi.vertical_line.sigPositionChanged.disconnect(
                self.crosshair_roi_changed
            )
            self.crosshair_roi.horizontal_line.sigPositionChanged.disconnect(
                self.crosshair_roi_changed
            )

    def set_profiles_visibility(self, visible, ignore_connections=False):
        for item in [self.full_hori_trace, self.full_vert_trace]:
            item.setVisible(visible)

    def set_roi_visibility(self, visible, ignore_connections=False):
        if visible:
            self.roi.setState(self.saved_roi_state)
            pos_i, pos_j = map(int, self.roi.pos())
            size_i, size_j = map(int, self.roi.size())
        else:
            self.saved_roi_state = self.roi.saveState()

        for item in [
            self.left_roi_trace,
            self.bottom_roi_trace,
            self.roi,
            self.roi_histogram.item.plot,
        ]:
            item.setVisible(visible)

        if ignore_connections:
            return

        if visible:
            self.roi.sigRegionChangeFinished.connect(self.roi_changed)
            self.image_item.sigImageChanged.connect(self.roi_changed)
        else:
            self.roi.sigRegionChangeFinished.disconnect(self.roi_changed)
            self.image_item.sigImageChanged.disconnect(self.roi_changed)

    def set_line_roi_visibility(self, visible, ignore_connections=False):
        if visible:
            self.line_roi.setState(self.saved_line_roi_state)
            pos_i, pos_j = map(int, self.line_roi.pos())
            size_i, size_j = map(int, self.line_roi.size())
        else:
            self.saved_line_roi_state = self.line_roi.saveState()

        for item in [
            self.line_roi,
            self.line_roi_trace,
            self.line_roi_trace_left,
            self.line_roi_trace_right,
        ]:
            item.setVisible(visible)

        if ignore_connections:
            return

        if visible:
            self.line_roi.sigRegionChanged.connect(self.line_roi_changed)
            self.image_item.sigImageChanged.connect(self.line_roi_changed)
        else:
            self.line_roi.sigRegionChanged.disconnect(self.line_roi_changed)
            self.image_item.sigImageChanged.disconnect(self.line_roi_changed)

    def set_roi_plotwidgets_visibility(self, visible):
        for item in [
            self.left_plot,
            self.bottom_plot,
            self.line_plot,
            self.roi_histogram,
        ]:
            item.setVisible(visible)

        self.left_plot.setMouseEnabled(visible, visible)
        self.bottom_plot.setMouseEnabled(visible, visible)

        if visible and (
            self.image_view_controller.roi_cb.isChecked()
            or self.image_view_controller.roi_crosshair_cb.isChecked()
            or self.image_view_controller.line_roi_cb.isChecked()
            or self.image_view_controller.profile_cb.isChecked()
        ):
            if not self.image_view_controller.roi_cb.isChecked():
                self.roi_histogram.item.plot.hide()
                self.left_roi_trace.hide()
                self.bottom_roi_trace.hide()
            if not self.image_view_controller.roi_crosshair_cb.isChecked():
                self.crosshair_roi.vertical_line.hide()
                self.crosshair_roi.horizontal_line.hide()
                self.left_crosshair_roi.hide()
                self.bottom_crosshair_roi.hide()
            if not self.image_view_controller.line_roi_cb.isChecked():
                self.line_roi_trace.hide()
                self.line_roi_trace_left.hide()
                self.line_roi_trace_right.hide()
            if not self.image_view_controller.profile_cb.isChecked():
                self.full_hori_trace.hide()
                self.full_vert_trace.hide()

    def hide_crosshair_roi(self, ignore_connections=False):
        self.set_crosshair_roi_visibility(False, ignore_connections)

    def show_crosshair_roi(self, ignore_connections=False):
        self.set_crosshair_roi_visibility(True, ignore_connections)
        self.crosshair_roi_changed()

    def show_profiles(self, ignore_connections=False):
        self.set_profiles_visibility(True, ignore_connections)
        self.update_trace()

    def hide_profiles(self, ignore_connections=False):
        self.set_profiles_visibility(False, ignore_connections)

    def hide_roi(self, ignore_connections=False):
        self.set_roi_visibility(False, ignore_connections)

    def show_roi(self, ignore_connections=False):
        self.set_roi_visibility(True, ignore_connections)
        self.roi_changed()

    def show_line_roi(self, ignore_connections=False):
        self.set_line_roi_visibility(True, ignore_connections)
        self.line_roi_changed()

    def hide_line_roi(self, ignore_connections=False):
        self.set_line_roi_visibility(False, ignore_connections)

    def hide_roi_plotwidgets(self):
        self.set_roi_plotwidgets_visibility(False)

    def show_roi_plotwidgets(self):
        self.set_roi_plotwidgets_visibility(True)

    def mousePressEvent(self, event):
        self.clicked.emit(self.name)

    def add_selected_pixel(self):
        pos = self.image_item.last_clicked
        if pos is not None and pos not in self.selected_pixels and self.select_pixels:
            self.selected_pixels.append(pos)

    def _drag_pos_to_world(self, x, y):
        """
        Convert drag coordinates (from CustomImageItem.dragData) into
        the world coordinate system used by the image and ROIs.

        Cases:
        - If metric length scaling is active (_use_metric_length), the
          CustomImageItem already emits metric units → return as-is.
        - If we have no axis-world extents (no labels), keep pixel coords.
        - If labels define world extents, map pixel indices 0..N-1 linearly
          into [x_min..x_max], [y_min..y_max].
        """
        img = self.image_item.image
        if img is None:
            return x, y

        # Camera/metric panel: CustomImageItem already converted to mm
        if self._use_metric_length:
            return x, y

        # No axis labels → remain in pixel coordinates, as before
        if self._axis_world_extents is None:
            return x, y

        nx, ny = img.shape[:2]
        if nx <= 0 or ny <= 0:
            return x, y

        x_min, x_max, y_min, y_max = self._axis_world_extents

        sx = (x_max - x_min) / float(nx)
        sy = (y_max - y_min) / float(ny)

        # Use bin centres; edges vs centres is a small offset only
        wx = x_min + (float(x) + 0.5) * sx
        wy = y_min + (float(y) + 0.5) * sy

        return wx, wy

    def enter_roi_drag_mode(self):
        if self._line_roi_drag_active:
            self.exit_line_roi_drag_mode()
        elif self._roi_drag_active:
            self.exit_roi_drag_mode()
        if not self.image_view_controller.roi_cb.isChecked():
            self.image_view_controller.roi_cb.click()
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.view.setMouseEnabled(False, False)
        self.roi.setPos(self.view.viewRect().center())
        self.roi.setSize((0, 0))
        self.image_item.set_define_roi_mode(True)
        self.image_item.dragData.connect(self.define_roi)
        self._roi_drag_active = True

    def exit_roi_drag_mode(self):
        self.image_item.set_define_roi_mode(False)
        self.image_item.dragData.disconnect(self.define_roi)
        self.view.setMouseEnabled(True, True)
        QApplication.restoreOverrideCursor()
        self._roi_drag_active = False

    def enter_line_roi_drag_mode(self):
        if self._line_roi_drag_active:
            self.exit_line_roi_drag_mode()
        elif self._roi_drag_active:
            self.exit_roi_drag_mode()
        if not self.image_view_controller.line_roi_cb.isChecked():
            self.image_view_controller.line_roi_cb.click()
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.view.setMouseEnabled(False, False)
        center_ = self.view.viewRect().center()
        center_point = (center_.x(), center_.y())
        self.line_roi.set_pos(center_point, center_point, width=0)
        self.image_item.set_define_roi_mode(True)
        self.image_item.dragData.connect(self.define_line_roi)
        self._line_roi_drag_active = True

    def exit_line_roi_drag_mode(self):
        self.image_item.set_define_roi_mode(False)
        self.image_item.dragData.disconnect(self.define_line_roi)
        self.view.setMouseEnabled(True, True)
        QApplication.restoreOverrideCursor()
        self._line_roi_drag_active = False

    @pyqtSlot(tuple)
    def define_roi(self, data):
        dragging, start_coord, end_coord = data
        if not dragging:
            self.exit_roi_drag_mode()
            return

        x0_pix, y0_pix = start_coord
        x1_pix, y1_pix = end_coord

        # Convert drag (pixel) coordinates to world coordinates
        x0, y0 = self._drag_pos_to_world(x0_pix, y0_pix)
        x1, y1 = self._drag_pos_to_world(x1_pix, y1_pix)

        left = min(x0, x1)
        top = min(y0, y1)
        width = abs(x1 - x0)
        height = abs(y1 - y0)

        self.roi.setPos(left, top)
        self.roi.setSize((width, height))

    @pyqtSlot(tuple)
    def define_line_roi(self, data):
        dragging, start_coord, end_coord = data
        if not dragging:
            self.exit_line_roi_drag_mode()
            return

        x0_pix, y0_pix = start_coord
        x1_pix, y1_pix = end_coord

        # Convert drag (pixel) coordinates to world coordinates
        p1 = self._drag_pos_to_world(x0_pix, y0_pix)
        p2 = self._drag_pos_to_world(x1_pix, y1_pix)

        self.line_roi.set_pos(p1, p2)

    def toggle_log_mode(self, log_mode):
        enabled = bool(log_mode)
        self.log_mode = enabled

        if hasattr(self, "logScaleAction"):
            self.logScaleAction.blockSignals(True)
            self.logScaleAction.setChecked(enabled)
            self.logScaleAction.blockSignals(False)

        ctrl = getattr(self, "image_view_controller", None)
        if ctrl is not None and hasattr(ctrl, "log_cb"):
            ctrl.log_cb.blockSignals(True)
            ctrl.log_cb.setChecked(enabled)
            ctrl.log_cb.blockSignals(False)

        # colormap
        current_cm = self.settings_histogram.item.gradient.colorMap()
        if enabled:
            self.saved_cm = current_cm
            new_cm = self._create_log_colormap(current_cm)
            self.settings_histogram.item.gradient.setColorMap(new_cm)
        else:
            self._restore_original_colormap()

        # side traces axes
        if hasattr(self, "left_plot"):
            self.left_plot.setLogMode(x=enabled, y=False)
        if hasattr(self, "bottom_plot"):
            self.bottom_plot.setLogMode(x=False, y=enabled)

    def update_scale(self, state):
        self._use_metric_length = state
        self._pix_to_mm_ratio = self.image_view_controller.pix_to_mm_ratio

        self._update_labels()

        self._update_roi_scaling()
        self._update_line_roi_scaling()
        self._update_crosshair_roi_scaling()

        self.image_item.set_metric_mode(state, self._pix_to_mm_ratio)

        self._update_image_rect()
        self.roi_changed()
        self.line_roi_changed()
        self.crosshair_roi_changed()
        self.update_trace()
        self.settings_histogram.item.imageChanged()

    def _update_labels(self):
        if self._use_metric_length:
            self.left_plot.setLabel("left", "mm")
            self.bottom_plot.setLabel("bottom", "mm")
            self.line_plot.setLabel("bottom", "mm")
        else:
            self.left_plot.setLabel("left", "Pixels")
            self.bottom_plot.setLabel("bottom", "Pixels")
            self.line_plot.setLabel("bottom", "Pixels")

    def _handle_image_labels(self, labels):
        image = self.image_item.image
        if image is None:
            self.log.warning("No image data available when handling labels.")
            return

        if not (
            hasattr(self, "custom_bottom_axis") and hasattr(self, "custom_left_axis")
        ):
            self.log.warning("No custom axes available when handling labels.")
            return

        # image is stored as (nx, ny) after the transpose in set_data()
        nx, ny = image.shape[:2]

        def to_array(key):
            arr = labels.get(key)
            if arr is None:
                return None
            try:
                return np.asarray(arr, dtype=float)
            except Exception as e:
                self.log.error("Error converting %r labels: %s", key, e)
                return None

        x_labels = to_array("x")
        y_labels = to_array("y")

        def compute_min_max(label_arr, n_samples):
            if label_arr is None:
                return 0.0, float(n_samples)
            size = label_arr.size
            if size == n_samples + 1:
                # bin edges
                return float(label_arr[0]), float(label_arr[-1])
            elif size == n_samples:
                # bin centers, build edges by assuming constant spacing
                if size > 1:
                    step = float(label_arr[1] - label_arr[0])
                else:
                    step = 1.0
                return (
                    float(label_arr[0] - step / 2.0),
                    float(label_arr[-1] + step / 2.0),
                )
            else:
                # fallback
                return float(label_arr.min()), float(label_arr.max())

        x_min, x_max = compute_min_max(x_labels, nx)
        y_min, y_max = compute_min_max(y_labels, ny)

        self._axis_world_extents = (
            float(x_min),
            float(x_max),
            float(y_min),
            float(y_max),
        )

        # Set the image rect in world coordinates (Å, ΔE, etc.)
        self.image_item.setRect(x_min, y_min, x_max - x_min, y_max - y_min)

        # Precompute per-pixel world coordinates (centers) for each axis.
        # These are used by the full profiles and crosshair projections.
        if x_max != x_min:
            self.x_axis_coords = x_min + (np.arange(nx, dtype=float) + 0.5) * (
                (x_max - x_min) / nx
            )
        else:
            self.x_axis_coords = np.zeros(nx, dtype=float)

        if y_max != y_min:
            self.y_axis_coords = y_min + (np.arange(ny, dtype=float) + 0.5) * (
                (y_max - y_min) / ny
            )
        else:
            self.y_axis_coords = np.zeros(ny, dtype=float)

        # Feed original label arrays to the custom axes for tick text
        if x_labels is not None:
            self.custom_bottom_axis.setLabelsArray(x_labels)
        if y_labels is not None:
            self.custom_left_axis.setLabelsArray(y_labels)

    def set_image_axes_visible(self, visible: bool):
        """Show or hide the axes and tick labels on the main image plot."""
        self.image_plot.showAxis("bottom", visible)
        self.image_plot.showAxis("left", visible)

    def _pix_to_mm(self, pix):
        return pix * self._pix_to_mm_ratio

    def _mm_to_pix(self, mm):
        return mm / self._pix_to_mm_ratio

    def _update_image_rect(self):
        if self.image_item.image is None:
            return
        if self._use_metric_length:
            # Define the display dimensions in millimeters (or scene units)
            display_width_mm = self.image_item.image.shape[0] * self._pix_to_mm_ratio
            display_height_mm = self.image_item.image.shape[1] * self._pix_to_mm_ratio

            # Set the display rectangle for the ImageItem
            self.image_item.setRect(0, 0, display_width_mm, display_height_mm)
        else:
            self.image_item.setRect(
                0,
                0,
                self.image_item.image.shape[0],
                self.image_item.image.shape[1],
            )

    def _update_roi_scaling(self):
        should_disconnect = self.roi.isVisible()
        if should_disconnect:
            self.roi.sigRegionChangeFinished.disconnect(self.roi_changed)
        if self._use_metric_length:
            pos = self.roi.pos()
            size = self.roi.size()
            self.roi.setPos(self._pix_to_mm(pos.x()), self._pix_to_mm(pos.y()))
            self.roi.setSize((self._pix_to_mm(size.x()), self._pix_to_mm(size.y())))
        else:
            pos = self.roi.pos()
            size = self.roi.size()
            self.roi.setPos(self._mm_to_pix(pos.x()), self._mm_to_pix(pos.y()))
            self.roi.setSize((self._mm_to_pix(size.x()), self._mm_to_pix(size.y())))
        if should_disconnect:
            self.roi.sigRegionChangeFinished.connect(self.roi_changed)

    def _update_line_roi_scaling(self):
        should_disconnect = self.line_roi.isVisible()
        if should_disconnect:
            self.line_roi.sigRegionChanged.disconnect(self.line_roi_changed)
        if self._use_metric_length:
            pos1, pos2 = self.line_roi.get_pos()
            width = self.line_roi.get_width()
            self.line_roi.set_pos(
                (self._pix_to_mm(pos1.x()), self._pix_to_mm(pos1.y())),
                (self._pix_to_mm(pos2.x()), self._pix_to_mm(pos2.y())),
                self._pix_to_mm(width),
            )
        else:
            pos1, pos2 = self.line_roi.get_pos()
            width = self.line_roi.get_width()
            self.line_roi.set_pos(
                (self._mm_to_pix(pos1.x()), self._mm_to_pix(pos1.y())),
                (self._mm_to_pix(pos2.x()), self._mm_to_pix(pos2.y())),
                self._mm_to_pix(width),
            )
        if should_disconnect:
            self.line_roi.sigRegionChanged.connect(self.line_roi_changed)

    def _update_crosshair_roi_scaling(self):
        should_disconnect = self.crosshair_roi.vertical_line.isVisible()
        if should_disconnect:
            self.crosshair_roi.vertical_line.sigPositionChanged.disconnect(
                self.crosshair_roi_changed
            )
            self.crosshair_roi.horizontal_line.sigPositionChanged.disconnect(
                self.crosshair_roi_changed
            )

        if self._use_metric_length:
            self.crosshair_roi.vertical_line.setValue(
                self._pix_to_mm(self.crosshair_roi.vertical_line.value())
            )
            self.crosshair_roi.horizontal_line.setValue(
                self._pix_to_mm(self.crosshair_roi.horizontal_line.value())
            )
        else:
            self.crosshair_roi.vertical_line.setValue(
                self._mm_to_pix(self.crosshair_roi.vertical_line.value())
            )
            self.crosshair_roi.horizontal_line.setValue(
                self._mm_to_pix(self.crosshair_roi.horizontal_line.value())
            )
        if should_disconnect:
            self.crosshair_roi.vertical_line.sigPositionChanged.connect(
                self.crosshair_roi_changed
            )
            self.crosshair_roi.horizontal_line.sigPositionChanged.connect(
                self.crosshair_roi_changed
            )

    def _colormap_changed_from_menu(self):
        self.saved_cm = self.settings_histogram.item.gradient.colorMap()

        if self.log_mode:
            new_cm = self._create_log_colormap(self.saved_cm)
            self.settings_histogram.item.gradient.setColorMap(new_cm)
        else:
            self._restore_original_colormap()

    def _create_log_colormap(self, current_cm):
        colors = current_cm.getColors(mode="byte")
        pos = current_cm.pos
        new_pos = np.exp(np.linspace(-5, 0, 10))
        new_pos[0], new_pos[-1] = 0.0, 1.0
        new_colors = [
            [int(np.interp(x, pos, c)) for c in zip(*colors)]
            for x in np.linspace(0, 1, 10)
        ]

        return ColorMap(np.array(new_pos), np.array(new_colors, dtype=np.ubyte))

    def _restore_original_colormap(self):
        if self.saved_cm is not None:
            self.settings_histogram.item.gradient.setColorMap(self.saved_cm)

    def set_data(self, arrays, labels, autoLevels=False):
        self.set_image(
            np.array(arrays[0]).T.astype(np.float64),
            autoLevels=autoLevels,
        )

        if labels:
            self._handle_image_labels(labels)

    def set_axis_labels(self, x_label, x_unit, y_label, y_unit):
        """Apply image axis labels/units to side plots."""
        if hasattr(self, "bottom_plot"):
            self.bottom_plot.setLabel("bottom", x_label, units=x_unit)
        if hasattr(self, "left_plot"):
            self.left_plot.setLabel("left", y_label, units=y_unit)
        # if hasattr(self, "line_plot"): # we probably don't want to change this because it's a profile along arbitrary line
        #     self.line_plot.setLabel("bottom", x_label, units=x_unit)

    def save_state(self):
        return {
            "saved_roi_state": self.roi.saveState(),
            "saved_line_roi_state": self.line_roi.saveState(),
            "saved_lut_state": self.settings_histogram.item.gradient.saveState(),
            "saved_levels": self.image_item.getLevels(),
            "saved_cross_roi": (
                self.crosshair_roi.vertical_line.value(),
                self.crosshair_roi.horizontal_line.value(),
            ),
        }

    def restore_state(self, state):
        self.roi.setState(state["saved_roi_state"])
        self.line_roi.setState(state["saved_line_roi_state"])
        self.settings_histogram.item.gradient.restoreState(state["saved_lut_state"])
        self.image_item.setLevels(state["saved_levels"])
        self.crosshair_roi.vertical_line.setValue(state["saved_cross_roi"][0])
        self.crosshair_roi.horizontal_line.setValue(state["saved_cross_roi"][1])

    @pyqtSlot(str)
    def set_hover_title(self, title):
        self.hover_label.setText(title)

    @pyqtSlot()
    def update_trace(self):
        if self.image_item.image is None:
            return

        image = self.image_item.image
        nx, ny = image.shape[:2]

        # Full horizontal trace (bottom plot): mean over y → function of x
        hori_y = image.mean(axis=1)  # length nx

        # Full vertical trace (left plot): mean over x → function of y
        vert_y = image.mean(axis=0)  # length ny

        x_coords = getattr(self, "x_axis_coords", None)
        y_coords = getattr(self, "y_axis_coords", None)

        if x_coords is not None and x_coords.size == hori_y.size:
            hori_x_axis = x_coords
        else:
            hori_x_axis = np.arange(hori_y.size, dtype=float)

        if y_coords is not None and y_coords.size == vert_y.size:
            vert_axis = y_coords
        else:
            vert_axis = np.arange(vert_y.size, dtype=float)

        # bottom plot: intensity vs x
        self.full_hori_trace.setData(x=hori_x_axis, y=hori_y)

        # left plot: intensity vs y
        self.full_vert_trace.setData(x=vert_y, y=vert_axis)

    @pyqtSlot()
    def splitter_moved(self, sender):
        receiver = (
            self.splitter_vert_1
            if sender is self.splitter_vert_2
            else self.splitter_vert_2
        )
        receiver.blockSignals(True)
        receiver.setSizes(sender.sizes())
        receiver.blockSignals(False)

    @pyqtSlot()
    def update_hist_levels_text(self):
        hist_min, hist_max = self.image_item.getLevels()
        self.image_view_controller.hist_max_level_le.setText(str(round(hist_max, 5)))
        self.image_view_controller.hist_min_level_le.setText(str(round(hist_min, 5)))

    def _format_float(self, value, precision=3):
        if value == int(value):
            return f"{int(value)}"
        else:
            return f"{value:.{precision}f}"

    @pyqtSlot()
    def crosshair_roi_changed(self):
        if self.image_item.image is None:
            return

        image = self.image_item.image
        nx, ny = image.shape[:2]

        x_coords = getattr(self, "x_axis_coords", None)
        y_coords = getattr(self, "y_axis_coords", None)

        def coord_to_index(coord, axis_coords, max_index):
            if axis_coords is None or axis_coords.size == 0:
                idx = int(np.floor(coord))
            else:
                idx = int(np.searchsorted(axis_coords, coord))
                if idx <= 0:
                    idx = 0
                elif idx >= axis_coords.size:
                    idx = axis_coords.size - 1
                else:
                    # snap to nearest bin center
                    if abs(coord - axis_coords[idx - 1]) < abs(
                        coord - axis_coords[idx]
                    ):
                        idx = idx - 1
            return max(0, min(max_index - 1, idx))

        # vertical_line is x, horizontal_line is y in world coordinates
        x_pos = self.crosshair_roi.vertical_line.value()
        y_pos = self.crosshair_roi.horizontal_line.value()

        x_index = coord_to_index(x_pos, x_coords, nx)
        y_index = coord_to_index(y_pos, y_coords, ny)

        # Profile along y at fixed x (vertical crosshair → left plot)
        slice_x = image[x_index, :]  # length ny

        # Profile along x at fixed y (horizontal crosshair → bottom plot)
        slice_y = image[:, y_index]  # length nx

        self.v_mean = np.mean(slice_x)
        self.v_std = np.std(slice_x)
        self.v_min = np.min(slice_x)
        self.v_max = np.max(slice_x)

        self.h_mean = np.mean(slice_y)
        self.h_std = np.std(slice_y)
        self.h_min = np.min(slice_y)
        self.h_max = np.max(slice_y)

        # Axes for the projections
        if y_coords is not None and y_coords.size == slice_x.size:
            left_y = y_coords
        else:
            left_y = np.arange(slice_x.size, dtype=float)

        if x_coords is not None and x_coords.size == slice_y.size:
            bottom_x = x_coords
        else:
            bottom_x = np.arange(slice_y.size, dtype=float)

        # left plot: intensity vs y
        self.left_crosshair_roi.setData(y=left_y, x=slice_x)

        # bottom plot: intensity vs x
        self.bottom_crosshair_roi.setData(x=bottom_x, y=slice_y)

        # Show world coordinates in controller
        self.image_view_controller.crosshair_roi_pos_x_le.setText(
            self._format_float(x_pos)
        )
        self.image_view_controller.crosshair_roi_pos_y_le.setText(
            self._format_float(y_pos)
        )

        # Linked guide lines in side plots use the same world coordinates
        self.left_crosshair_roi_hline.setPos(y_pos)
        self.bottom_crosshair_roi_vline.setPos(x_pos)

    @pyqtSlot()
    def roi_changed(self):
        # Extract image data from ROI
        if self.image_item.image is None:
            return

        if self.roi.size()[0] == 0 or self.roi.size()[1] == 0:
            return

        image = self.image_item.image
        nx, ny = image.shape[:2]

        x_coords = getattr(self, "x_axis_coords", None)
        y_coords = getattr(self, "y_axis_coords", None)

        # ROI bounds in world coordinates (same coordinate system as the image)
        pos = self.roi.pos()
        size = self.roi.size()

        x0 = float(pos.x())
        y0 = float(pos.y())
        x1 = x0 + float(size.x())
        y1 = y0 + float(size.y())

        def coord_range_to_indices(c0, c1, coords, n):
            lo, hi = sorted([c0, c1])
            if coords is None or len(coords) == 0:
                # fall back to pixel indices
                i0 = int(np.floor(lo))
                i1 = int(np.ceil(hi))
            else:
                i0 = int(np.searchsorted(coords, lo, side="left"))
                i1 = int(np.searchsorted(coords, hi, side="right"))

            i0 = max(0, min(n - 1, i0))
            i1 = max(i0 + 1, min(n, i1))
            return i0, i1

        # x is first axis, y is second axis in the internal image
        ix0, ix1 = coord_range_to_indices(x0, x1, x_coords, nx)
        iy0, iy1 = coord_range_to_indices(y0, y1, y_coords, ny)

        roi_data = image[ix0:ix1, iy0:iy1]
        if roi_data.size == 0:
            return

        # Histogram on ROI
        self.histogram_image_item.setImage(roi_data, autoLevels=False)
        self.roi_histogram.item.imageChanged(bins=100)

        # Projections over ROI
        data_x = roi_data.mean(axis=1)  # vs x
        data_y = roi_data.mean(axis=0)  # vs y

        if x_coords is not None and x_coords.size >= ix1:
            xvals = x_coords[ix0:ix1]
        else:
            xvals = np.arange(ix0, ix1, dtype=float)

        if y_coords is not None and y_coords.size >= iy1:
            yvals = y_coords[iy0:iy1]
        else:
            yvals = np.arange(iy0, iy1, dtype=float)

        # bottom plot: intensity vs x (linked to image X axis)
        self.bottom_roi_trace.setData(x=xvals, y=data_x)

        # left plot: intensity vs y (linked to image Y axis)
        self.left_roi_trace.setData(y=yvals, x=data_y)

        # ROI statistics
        self.roi_mean = roi_data.mean()
        self.roi_std = roi_data.std()
        self.roi_max = roi_data.max()
        self.roi_min = roi_data.min()

        # Update controller fields with world coordinates
        start_x = self._format_float(min(x0, x1))
        start_y = self._format_float(min(y0, y1))
        size_x = self._format_float(abs(x1 - x0))
        size_y = self._format_float(abs(y1 - y0))

        self.image_view_controller.roi_start_x_le.setText(start_x)
        self.image_view_controller.roi_start_y_le.setText(start_y)
        self.image_view_controller.roi_size_x_le.setText(size_x)
        self.image_view_controller.roi_size_y_le.setText(size_y)

    @pyqtSlot()
    def line_roi_changed(self):
        # Extract image data from ROI
        if self.image_item.image is None:
            return

        if self.line_roi.size()[0] == 0 or self.line_roi.size()[1] == 0:
            return

        if self.image_item.axisOrder == "col-major":
            axes = (self.axes["x"], self.axes["y"])
        else:
            axes = (self.axes["y"], self.axes["x"])

        data, coords = self.line_roi.getArrayRegion(
            self.image_item.image.view(np.ndarray),
            img=self.image_item,
            axes=axes,
            returnMappedCoords=True,
        )

        if data is None:
            return

        data_x = data.mean(axis=self.axes["y"])
        self.line_roi_mean = data.mean()
        self.line_roi_std = data.std()
        self.line_roi_max = data.max()
        self.line_roi_min = data.min()

        coords_x = coords[:, :, 0] - coords[:, 0:1, 0]
        xvals = (coords_x**2).sum(axis=0) ** 0.5

        self.line_roi_trace.setData(x=xvals, y=data_x)
        self.line_roi_trace_left.setData(x=[xvals[0]], y=[data_x[0]])
        self.line_roi_trace_right.setData(x=[xvals[-1]], y=[data_x[-1]])

        pos1, pos2 = self.line_roi.get_pos()
        width = self.line_roi.get_width()
        self.image_view_controller.line_roi_start_x_le.setText(
            self._format_float(pos1.x())
        )
        self.image_view_controller.line_roi_start_y_le.setText(
            self._format_float(pos1.y())
        )
        self.image_view_controller.line_roi_end_x_le.setText(
            self._format_float(pos2.x())
        )
        self.image_view_controller.line_roi_end_y_le.setText(
            self._format_float(pos2.y())
        )
        self.image_view_controller.line_roi_width_le.setText(self._format_float(width))

        length = np.sqrt((pos1.x() - pos2.x()) ** 2 + (pos1.y() - pos2.y()) ** 2)

        self.image_view_controller.current_line_length_rb.setText(
            self._format_float(length)
        )

    def set_image(self, image, autoLevels=True, raw_update=True):
        self.image_item.setImage(
            self.get_processed_image(image, raw_update), autoLevels=autoLevels
        )

    def update_image(self, force_image=None):
        if force_image is None:
            use_image = self.raw_image
            raw_update = True
        else:
            use_image = force_image
            raw_update = False
        self.image_item.setImage(
            self.get_processed_image(use_image, raw_update=raw_update),
            autoLevels=False,
        )

    def get_processed_image(self, image, raw_update=True):
        if raw_update:
            self.raw_image = np.copy(image)

        if (self.autolevel_on_update or not self.autolevel_complete) and image.size:
            flat_im = np.sort(image.ravel())
            ll, hl = int(len(flat_im) * 0.05), int(len(flat_im) * 0.95)
            use_min, use_max = flat_im[[ll, hl]]
            self.image_item.setLevels([use_min, use_max])
            self.autolevel_complete = True
        return image
