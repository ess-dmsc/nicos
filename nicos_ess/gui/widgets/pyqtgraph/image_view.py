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

    def __init__(self, parent=None, name="", histogram_orientation="horizontal", *args):
        QWidget.__init__(self, parent, *args)
        self.parent = parent
        self.name = name
        self.histogram_orientation = histogram_orientation

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
        self.axes = {"t": None, "x": 0, "y": 1, "c": None}

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

        for child in self.view.menu.actions():
            if child.text() == "View All":
                child.triggered.connect(self.set_auto_scale_axis)

    def set_auto_scale_axis(self):
        self.view.enableAutoRange(x=True, y=True)

    def set_aspect_locked(self):
        self.image_plot.setAspectLocked(self.aspectLockedAction.isChecked())

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
        self.left_plot.plotItem.invertY()
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

        self.splitter_vert_3 = QSplitter(Qt.Orientation.Vertical)
        # self.splitter_vert_3.addWidget(self.image_view_controller)
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

    def set_aspect_locked(self, state):
        self.image_plot.setAspectLocked(state)

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

    def enter_roi_drag_mode(self):
        if self._line_roi_drag_active:
            self.exit_line_roi_drag_mode()
        elif self._roi_drag_active:
            self.exit_roi_drag_mode()
        if not self.image_view_controller.roi_cb.isChecked():
            self.image_view_controller.roi_cb.click()
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.view.setMouseEnabled(False, False)
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
        if dragging:
            self.roi.setPos(*start_coord)
            raw_size = (
                end_coord[0] - start_coord[0],
                end_coord[1] - start_coord[1],
            )
            size = tuple(map(lambda x: max(x, 0), raw_size))
            self.roi.setSize(size=size)
        else:
            self.exit_roi_drag_mode()

    @pyqtSlot(tuple)
    def define_line_roi(self, data):
        dragging, start_coord, end_coord = data
        if dragging:
            self.line_roi.set_pos(start_coord, end_coord)
        else:
            self.exit_line_roi_drag_mode()

    def toggle_log_mode(self, log_mode):
        self.log_mode = log_mode

        current_cm = self.settings_histogram.item.gradient.colorMap()

        if log_mode:
            self.saved_cm = current_cm
            new_cm = self._create_log_colormap(current_cm)
            self.settings_histogram.item.gradient.setColorMap(new_cm)
        else:
            self._restore_original_colormap()

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

    def _handle_image_labels(self, labels):
        image = self.image_item.image
        if image is None:
            self.log.warning("No image data available when handling labels.")
            return

        if not (
            hasattr(self, "custom_bottom_axis") or hasattr(self, "custom_left_axis")
        ):
            self.log.warning("No custom axes available when handling labels.")
            return

        x_pixels, y_pixels = image.shape[0], image.shape[1]

        try:
            x_labels = np.asarray(labels.get("x"), dtype=float)
            y_labels = np.asarray(labels.get("y"), dtype=float)
        except Exception as e:
            self.log.error("Error converting labels: %s", e)
            return

        if x_labels is None or y_labels is None:
            self.log.warning("Missing 'x' or 'y' labels in _handle_image_labels.")
            return

        if x_labels.size == x_pixels + 1:
            x_min, x_max = x_labels[0], x_labels[-1]
        elif x_labels.size == x_pixels:
            dx = x_labels[1] - x_labels[0] if x_pixels > 1 else 1.0
            x_min, x_max = x_labels[0] - dx / 2.0, x_labels[-1] + dx / 2.0
        else:
            self.log.warning(
                "Unexpected number of x labels; defaulting to min/max from labels."
            )
            x_min, x_max = float(x_labels.min()), float(x_labels.max())

        if y_labels.size == y_pixels + 1:
            y_min, y_max = y_labels[0], y_labels[-1]
        elif y_labels.size == y_pixels:
            dy = y_labels[1] - y_labels[0] if y_pixels > 1 else 1.0
            y_min, y_max = y_labels[0] - dy / 2.0, y_labels[-1] + dy / 2.0
        else:
            self.log.warning(
                "Unexpected number of y labels; defaulting to min/max from labels."
            )
            y_min, y_max = float(y_labels.min()), float(y_labels.max())

        if self._use_metric_length:
            x_min, x_max = self._pix_to_mm(x_min), self._pix_to_mm(x_max)
            y_min, y_max = self._pix_to_mm(y_min), self._pix_to_mm(y_max)
            x_labels = self._pix_to_mm(x_labels)
            y_labels = self._pix_to_mm(y_labels)

        self.image_item.setRect(x_min, y_min, x_max - x_min, y_max - y_min)

        self.custom_bottom_axis.setLabelsArray(x_labels)
        self.custom_left_axis.setLabelsArray(y_labels)

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
        hori_y = self.image_item.image.mean(axis=1)
        vert_y = self.image_item.image.mean(axis=0)
        hori_x_axis = np.arange(0, len(hori_y))
        vert_x_axis = np.arange(0, len(vert_y))
        if self._use_metric_length:
            hori_x_axis = self._pix_to_mm(hori_x_axis)
            vert_x_axis = self._pix_to_mm(vert_x_axis)
        self.full_hori_trace.setData(y=hori_y, x=hori_x_axis)
        self.full_vert_trace.setData(x=vert_y, y=vert_x_axis)

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
        # Extract image data from ROI
        if self.image_item.image is None:
            return

        max_x, max_y = self.image_item.image.shape
        if self._use_metric_length:
            h_val = int(
                np.floor(self._mm_to_pix(self.crosshair_roi.horizontal_line.value()))
            )
            v_val = int(
                np.floor(self._mm_to_pix(self.crosshair_roi.vertical_line.value()))
            )
        else:
            h_val = int(np.floor(self.crosshair_roi.horizontal_line.value()))
            v_val = int(np.floor(self.crosshair_roi.vertical_line.value()))

        slice_point_y = min(max_y - 1, max(0, h_val))
        slice_point_x = min(max_x - 1, max(0, v_val))

        slice_x = self.image_item.image[slice_point_x, :]
        slice_y = self.image_item.image[:, slice_point_y]

        self.v_mean = np.mean(slice_x)
        self.v_std = np.std(slice_x)
        self.v_min = np.min(slice_x)
        self.v_max = np.max(slice_x)

        self.h_mean = np.mean(slice_y)
        self.h_std = np.std(slice_y)
        self.h_min = np.min(slice_y)
        self.h_max = np.max(slice_y)

        left_y = np.arange(0, len(slice_x))
        bottom_x = np.arange(0, len(slice_y))
        if self._use_metric_length:
            left_y = self._pix_to_mm(left_y)
            bottom_x = self._pix_to_mm(bottom_x)

        self.left_crosshair_roi.setData(y=left_y, x=slice_x)
        self.bottom_crosshair_roi.setData(x=bottom_x, y=slice_y)
        self.image_view_controller.crosshair_roi_pos_x_le.setText(
            self._format_float(v_val)
        )
        self.image_view_controller.crosshair_roi_pos_y_le.setText(
            self._format_float(h_val)
        )
        self.left_crosshair_roi_hline.setPos(self.crosshair_roi.horizontal_line.value())
        self.bottom_crosshair_roi_vline.setPos(self.crosshair_roi.vertical_line.value())

    @pyqtSlot()
    def roi_changed(self):
        # Extract image data from ROI
        if self.image_item.image is None:
            return

        if self.roi.size()[0] == 0 or self.roi.size()[1] == 0:
            return

        if self.image_item.axisOrder == "col-major":
            axes = (self.axes["x"], self.axes["y"])
        else:
            axes = (self.axes["y"], self.axes["x"])

        data, coords = self.roi.getArrayRegion(
            self.image_item.image.view(np.ndarray),
            img=self.image_item,
            axes=axes,
            returnMappedCoords=True,
        )

        if data is None:
            return

        self.histogram_image_item.setImage(data, autoLevels=False)
        self.roi_histogram.item.imageChanged(bins=100)

        data_x = data.mean(axis=self.axes["y"])
        data_y = data.mean(axis=self.axes["x"])
        self.roi_mean = data.mean()
        self.roi_std = data.std()
        self.roi_max = data.max()
        self.roi_min = data.min()

        x_ref, y_ref = np.floor(coords[0][0][0]), np.floor(coords[1][0][0])

        coords_x = coords[:, :, 0] - coords[:, 0:1, 0]
        coords_y = coords[:, 0, :] - coords[:, 0, 0:1]
        xvals = (coords_x**2).sum(axis=0) ** 0.5 + x_ref
        yvals = (coords_y**2).sum(axis=0) ** 0.5 + y_ref

        self.bottom_roi_trace.setData(x=xvals, y=data_x)
        self.left_roi_trace.setData(y=yvals, x=data_y)

        pos_i, pos_j = map(self._format_float, self.roi.pos())
        size_i, size_j = map(self._format_float, self.roi.size())
        self.image_view_controller.roi_start_x_le.setText(pos_i)
        self.image_view_controller.roi_start_y_le.setText(pos_j)
        self.image_view_controller.roi_size_x_le.setText(size_i)
        self.image_view_controller.roi_size_y_le.setText(size_j)

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

        if not self.autolevel_complete:
            flat_im = np.sort(image.flatten())
            ll, hl = int(len(flat_im) * 0.05), int(len(flat_im) * 0.95)
            use_min, use_max = flat_im[[ll, hl]]
            self.image_item.setLevels([use_min, use_max])
            self.autolevel_complete = True
        return image
