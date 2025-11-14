from nicos.guisupport.qt import (
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QIcon,
    QLabel,
    QLineEdit,
    QPushButton,
    QSize,
    Qt,
    QTimer,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from nicos_ess.gui.widgets.pyqtgraph.pixel_display_dialog import PixelDialog

CONTROLLER_REFRESH_INTERVAL = 1000


class ImageViewController(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.plotwidget = parent
        self.disp_image = None
        self.pix_to_mm_ratio = None

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.update_controller)
        self.refresh_timer.start(CONTROLLER_REFRESH_INTERVAL)

        self.build_ui()

    def initialize_ui(self):
        self.ui = QVBoxLayout()
        self.setLayout(self.ui)

    def create_hist_autoscale_btn(self):
        self.hist_autoscale_btn = QPushButton("Autoscale")
        self.hist_autoscale_btn.clicked.connect(self.single_shot_autoscale)

    def build_hist_settings(self):
        hist_settings_vbox = QVBoxLayout()
        level_settings_hbox = QHBoxLayout()

        level_low_hbox = QHBoxLayout()
        self.hist_min_level_le = QLineEdit()
        self.hist_min_level_le.setText("0")
        self.hist_min_level_le.setMinimumWidth(100)
        self.hist_min_level_le.setMaximumWidth(100)
        self.hist_min_level_le.returnPressed.connect(self.update_hist_min_level)
        hist_min_level_label = QLabel("Level low")
        level_low_hbox.addWidget(
            hist_min_level_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        level_low_hbox.addWidget(
            self.hist_min_level_le, alignment=Qt.AlignmentFlag.AlignLeft
        )
        level_settings_hbox.addLayout(level_low_hbox)

        level_high_hbox = QHBoxLayout()
        self.hist_max_level_le = QLineEdit()
        self.hist_max_level_le.setText("1")
        self.hist_max_level_le.setMinimumWidth(100)
        self.hist_max_level_le.setMaximumWidth(100)
        self.hist_max_level_le.returnPressed.connect(self.update_hist_max_level)
        hist_max_level_label = QLabel("Level high")
        level_high_hbox.addWidget(
            hist_max_level_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        level_high_hbox.addWidget(
            self.hist_max_level_le, alignment=Qt.AlignmentFlag.AlignLeft
        )
        level_settings_hbox.addLayout(level_high_hbox)

        self.log_cb = QCheckBox("Logarithmic mode")
        self.log_cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.log_cb.stateChanged.connect(self.toggle_log_mode)
        hist_settings_vbox.addLayout(level_settings_hbox)
        hist_settings_vbox.addWidget(self.log_cb)

        return hist_settings_vbox

    def build_roi_info_frame(self):
        self.roi_info_frame = QFrame()

        self.roi_info_vbox_layout = QVBoxLayout()

        self.roi_info_layout_frame = QFrame()
        self.roi_info_layout_frame.setFrameStyle(
            QFrame.Shape.WinPanel | QFrame.Shadow.Raised
        )
        self.roi_info_layout = QGridLayout()

        self.line_roi_info_layout_frame = QFrame()
        self.line_roi_info_layout_frame.setFrameStyle(
            QFrame.Shape.WinPanel | QFrame.Shadow.Raised
        )
        self.line_roi_info_layout = QGridLayout()

        self.crosshair_roi_info_layout_frame = QFrame()
        self.crosshair_roi_info_layout_frame.setFrameStyle(
            QFrame.Shape.WinPanel | QFrame.Shadow.Raised
        )
        self.crosshair_roi_info_layout = QGridLayout()

        self.selector_roi_info_layout_frame = QFrame()
        self.selector_roi_info_layout_frame.setFrameStyle(
            QFrame.Shape.WinPanel | QFrame.Shadow.Raised
        )
        self.selector_roi_info_layout = QGridLayout()

        self.build_roi_start_settings()
        self.build_roi_size_settings()
        self.build_line_roi_settings()
        self.build_crosshair_roi_settings()

        self.define_box_roi_btn = QToolButton()
        self.define_box_roi_btn.setIcon(QIcon("nicos_ess/gui/box.png"))
        self.define_box_roi_btn.setIconSize(QSize(30, 30))
        self.define_box_roi_btn.setToolTip("Drag to define a box ROI")
        self.define_box_roi_btn.clicked.connect(self.plotwidget.enter_roi_drag_mode)
        self.roi_cb = QCheckBox("Show")
        self.roi_cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.roi_cb.clicked.connect(self.roi_clicked)

        self.roi_info_layout.addWidget(self.define_box_roi_btn, 0, 0)
        self.roi_info_layout.addWidget(self.roi_cb, 0, 4)

        self.roi_info_layout.addWidget(self.roi_start_label, 1, 0)
        self.roi_info_layout.addWidget(
            self.roi_start_x_label, 1, 1, Qt.AlignmentFlag.AlignRight
        )
        self.roi_info_layout.addWidget(self.roi_start_x_le, 1, 2)
        self.roi_info_layout.addWidget(
            self.roi_start_y_label, 1, 3, Qt.AlignmentFlag.AlignRight
        )
        self.roi_info_layout.addWidget(self.roi_start_y_le, 1, 4)

        self.roi_info_layout.addWidget(self.roi_size_label, 2, 0)
        self.roi_info_layout.addWidget(
            self.roi_size_x_label, 2, 1, Qt.AlignmentFlag.AlignRight
        )
        self.roi_info_layout.addWidget(self.roi_size_x_le, 2, 2)
        self.roi_info_layout.addWidget(
            self.roi_size_y_label, 2, 3, Qt.AlignmentFlag.AlignRight
        )
        self.roi_info_layout.addWidget(self.roi_size_y_le, 2, 4)

        self.define_line_roi_btn = QToolButton()
        self.define_line_roi_btn.setIcon(QIcon("nicos_ess/gui/line.png"))
        self.define_line_roi_btn.setIconSize(QSize(30, 30))
        self.define_line_roi_btn.setToolTip("Drag to define a line ROI")
        self.define_line_roi_btn.clicked.connect(
            self.plotwidget.enter_line_roi_drag_mode
        )

        self.line_roi_cb = QCheckBox("Show")
        self.line_roi_cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.line_roi_cb.clicked.connect(self.line_roi_clicked)

        self.line_roi_info_layout.addWidget(self.define_line_roi_btn, 0, 0)
        self.line_roi_info_layout.addWidget(self.line_roi_cb, 0, 4)

        self.line_roi_info_layout.addWidget(self.line_roi_start_label, 1, 0)
        self.line_roi_info_layout.addWidget(
            self.line_roi_start_x_label, 1, 1, Qt.AlignmentFlag.AlignRight
        )
        self.line_roi_info_layout.addWidget(self.line_roi_start_x_le, 1, 2)
        self.line_roi_info_layout.addWidget(
            self.line_roi_start_y_label, 1, 3, Qt.AlignmentFlag.AlignRight
        )
        self.line_roi_info_layout.addWidget(self.line_roi_start_y_le, 1, 4)

        self.line_roi_info_layout.addWidget(self.line_roi_end_label, 2, 0)
        self.line_roi_info_layout.addWidget(
            self.line_roi_end_x_label, 2, 1, Qt.AlignmentFlag.AlignRight
        )
        self.line_roi_info_layout.addWidget(self.line_roi_end_x_le, 2, 2)
        self.line_roi_info_layout.addWidget(
            self.line_roi_end_y_label, 2, 3, Qt.AlignmentFlag.AlignRight
        )
        self.line_roi_info_layout.addWidget(self.line_roi_end_y_le, 2, 4)

        self.line_roi_info_layout.addWidget(self.line_roi_width_label, 3, 0)
        self.line_roi_info_layout.addWidget(self.line_roi_width_le, 3, 4)

        self.roi_crosshair_cb = QCheckBox("Show")
        self.roi_crosshair_cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.roi_crosshair_cb.clicked.connect(self.roi_crosshair_clicked)

        self.crosshair_roi_info_layout.addWidget(self.roi_crosshair_cb, 0, 4)

        self.crosshair_roi_info_layout.addWidget(self.crosshair_roi_pos_label, 1, 0)
        self.crosshair_roi_info_layout.addWidget(
            self.crosshair_roi_pos_x_label, 1, 1, Qt.AlignmentFlag.AlignRight
        )
        self.crosshair_roi_info_layout.addWidget(self.crosshair_roi_pos_x_le, 1, 2)
        self.crosshair_roi_info_layout.addWidget(
            self.crosshair_roi_pos_y_label, 1, 3, Qt.AlignmentFlag.AlignRight
        )
        self.crosshair_roi_info_layout.addWidget(self.crosshair_roi_pos_y_le, 1, 4)

        self.selector_roi_select_cb = QCheckBox("Select Pixels")
        self.selector_roi_select_cb.clicked.connect(self.selector_roi_select_clicked)

        self.selector_roi_counter_label = QLabel("Selected Pixels: 0")

        self.selector_roi_display_btn = QPushButton("Display Pixels")
        self.selector_roi_display_btn.clicked.connect(self.selector_roi_display)

        self.selector_roi_info_layout.addWidget(
            self.selector_roi_select_cb, 0, 0, Qt.AlignmentFlag.AlignLeft
        )
        self.selector_roi_info_layout.addWidget(
            self.selector_roi_counter_label, 0, 1, Qt.AlignmentFlag.AlignRight
        )

        self.selector_roi_info_layout.addWidget(self.selector_roi_display_btn, 1, 0)

        self.roi_info_layout_frame.setLayout(self.roi_info_layout)
        self.line_roi_info_layout_frame.setLayout(self.line_roi_info_layout)
        self.crosshair_roi_info_layout_frame.setLayout(self.crosshair_roi_info_layout)
        self.selector_roi_info_layout_frame.setLayout(self.selector_roi_info_layout)

        self.roi_info_vbox_layout.addWidget(self.roi_info_layout_frame)
        self.roi_info_vbox_layout.addWidget(self.line_roi_info_layout_frame)
        self.roi_info_vbox_layout.addWidget(self.crosshair_roi_info_layout_frame)
        self.roi_info_vbox_layout.addWidget(self.selector_roi_info_layout_frame)

        self.roi_info_frame.setLayout(self.roi_info_vbox_layout)

    def build_ui(self):
        self.initialize_ui()
        self.build_roi_info_frame()

        vbox = QVBoxLayout()

        hist_settings = self.build_hist_settings()
        self.create_hist_autoscale_btn()

        vbox.addLayout(hist_settings)

        self.profile_cb = QCheckBox("Show Full Profiles")
        self.profile_cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.profile_cb.clicked.connect(self.show_profile_clicked)
        vbox.addWidget(self.profile_cb)

        vbox.addWidget(self.roi_info_frame)

        scale_settings = self.build_scale_settings()
        vbox.addLayout(scale_settings)

        self.ui.addLayout(vbox)

    def build_roi_start_settings(self):
        self.roi_start_x_le = QLineEdit()
        self.roi_start_x_le.setText("0")
        self.roi_start_x_le.setMinimumWidth(100)
        self.roi_start_x_le.setMaximumWidth(100)
        self.roi_start_x_le.returnPressed.connect(self.update_roi_start_x)

        self.roi_start_y_le = QLineEdit()
        self.roi_start_y_le.setText("0")
        self.roi_start_y_le.setMinimumWidth(100)
        self.roi_start_y_le.setMaximumWidth(100)
        self.roi_start_y_le.returnPressed.connect(self.update_roi_start_y)

        self.roi_start_label = QLabel("ROI Start: ")
        self.roi_start_x_label = QLabel("X")
        self.roi_start_y_label = QLabel("Y")

    def build_roi_size_settings(self):
        self.roi_size_x_le = QLineEdit()
        self.roi_size_x_le.setText("0")
        self.roi_size_x_le.setMinimumWidth(100)
        self.roi_size_x_le.setMaximumWidth(100)
        self.roi_size_x_le.returnPressed.connect(self.update_roi_size_x)

        self.roi_size_y_le = QLineEdit()
        self.roi_size_y_le.setText("0")
        self.roi_size_y_le.setMinimumWidth(100)
        self.roi_size_y_le.setMaximumWidth(100)
        self.roi_size_y_le.returnPressed.connect(self.update_roi_size_y)

        self.roi_size_label = QLabel("ROI Size: ")
        self.roi_size_x_label = QLabel("X")
        self.roi_size_y_label = QLabel("Y")

    def build_scale_settings(self):
        scale_settings_vbox = QVBoxLayout()
        scale_settings_vbox.addStretch(1)

        line_length_hbox = QHBoxLayout()
        self.current_line_length_label = QLabel("Current line length: ")
        self.current_line_length_rb = QLabel("0")
        line_length_hbox.addWidget(self.current_line_length_label)
        line_length_hbox.addWidget(self.current_line_length_rb)

        defined_length_hbox = QHBoxLayout()
        self.defined_length_label = QLabel("Define length (mm): ")
        self.defined_length_le = QLineEdit()
        self.defined_length_le.setText("1")
        self.defined_length_le.setMinimumWidth(100)
        self.defined_length_le.setMaximumWidth(100)
        self.defined_length_le.returnPressed.connect(self.update_pix_mm_ratio)
        defined_length_hbox.addWidget(self.defined_length_label)
        defined_length_hbox.addWidget(
            self.defined_length_le, alignment=Qt.AlignmentFlag.AlignLeft
        )

        self.use_defined_length_cb = QCheckBox("Use defined length")
        self.use_defined_length_cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.use_defined_length_cb.stateChanged.connect(self.toggle_use_defined_length)
        self.use_defined_length_cb.setEnabled(False)

        pix_ratio_hbox = QHBoxLayout()
        self.pix_mm_ratio_label = QLabel("Pix/mm ratio: ")
        self.pix_mm_ratio_rb = QLabel("0")
        pix_ratio_hbox.addWidget(self.pix_mm_ratio_label)
        pix_ratio_hbox.addWidget(self.pix_mm_ratio_rb)

        scale_settings_vbox.addLayout(line_length_hbox)
        scale_settings_vbox.addLayout(defined_length_hbox)
        scale_settings_vbox.addLayout(pix_ratio_hbox)
        scale_settings_vbox.addWidget(self.use_defined_length_cb)

        return scale_settings_vbox

    def build_line_roi_settings(self):
        self.line_roi_start_x_le = QLineEdit()
        self.line_roi_start_x_le.setText("0")
        self.line_roi_start_x_le.setMinimumWidth(100)
        self.line_roi_start_x_le.setMaximumWidth(100)
        self.line_roi_start_x_le.returnPressed.connect(self.update_line_roi_start_x)

        self.line_roi_start_y_le = QLineEdit()
        self.line_roi_start_y_le.setText("0")
        self.line_roi_start_y_le.setMinimumWidth(100)
        self.line_roi_start_y_le.setMaximumWidth(100)
        self.line_roi_start_y_le.returnPressed.connect(self.update_line_roi_start_y)

        self.line_roi_end_x_le = QLineEdit()
        self.line_roi_end_x_le.setText("0")
        self.line_roi_end_x_le.setMinimumWidth(100)
        self.line_roi_end_x_le.setMaximumWidth(100)
        self.line_roi_end_x_le.returnPressed.connect(self.update_line_roi_end_x)

        self.line_roi_end_y_le = QLineEdit()
        self.line_roi_end_y_le.setText("0")
        self.line_roi_end_y_le.setMinimumWidth(100)
        self.line_roi_end_y_le.setMaximumWidth(100)
        self.line_roi_end_y_le.returnPressed.connect(self.update_line_roi_end_y)

        self.line_roi_width_le = QLineEdit()
        self.line_roi_width_le.setText("0")
        self.line_roi_width_le.setMinimumWidth(100)
        self.line_roi_width_le.setMaximumWidth(100)
        self.line_roi_width_le.returnPressed.connect(self.update_line_roi_width)

        self.line_roi_start_label = QLabel("Line ROI Start: ")
        self.line_roi_start_x_label = QLabel("X")
        self.line_roi_start_y_label = QLabel("Y")

        self.line_roi_end_label = QLabel("Line ROI End: ")
        self.line_roi_end_x_label = QLabel("X")
        self.line_roi_end_y_label = QLabel("Y")
        self.line_roi_width_label = QLabel("Line Width: ")

    def build_crosshair_roi_settings(self):
        self.crosshair_roi_pos_x_le = QLineEdit()
        self.crosshair_roi_pos_x_le.setText("0")
        self.crosshair_roi_pos_x_le.setMinimumWidth(100)
        self.crosshair_roi_pos_x_le.setMaximumWidth(100)
        self.crosshair_roi_pos_x_le.returnPressed.connect(self.update_crosshair_roi_x)

        self.crosshair_roi_pos_y_le = QLineEdit()
        self.crosshair_roi_pos_y_le.setText("0")
        self.crosshair_roi_pos_y_le.setMinimumWidth(100)
        self.crosshair_roi_pos_y_le.setMaximumWidth(100)
        self.crosshair_roi_pos_y_le.returnPressed.connect(self.update_crosshair_roi_y)

        self.crosshair_roi_pos_label = QLabel("Cross Pos: ")
        self.crosshair_roi_pos_x_label = QLabel("X")
        self.crosshair_roi_pos_y_label = QLabel("Y")

    def toggle_use_defined_length(self, state):
        use_defined_length = state == Qt.Checked
        self.plotwidget.update_scale(use_defined_length)

    def update_pix_mm_ratio(self):
        self.pix_to_mm_ratio = float(self.defined_length_le.text()) / float(
            self.current_line_length_rb.text()
        )
        self.pix_mm_ratio_rb.setText(str(round(self.pix_to_mm_ratio, 3)))

        if self.pix_to_mm_ratio <= 0:
            self.pix_to_mm_ratio = None
            self.use_defined_length_cb.setEnabled(False)
        else:
            self.use_defined_length_cb.setEnabled(True)

    def update_roi_start_x(self):
        self.plotwidget.roi.setPos(
            float(self.roi_start_x_le.text()), self.plotwidget.roi.pos()[1]
        )

    def update_roi_start_y(self):
        self.plotwidget.roi.setPos(
            self.plotwidget.roi.pos()[0], float(self.roi_start_y_le.text())
        )

    def update_roi_size_x(self):
        self.plotwidget.roi.setSize(
            [float(self.roi_size_x_le.text()), self.plotwidget.roi.size()[1]]
        )

    def update_roi_size_y(self):
        self.plotwidget.roi.setSize(
            [self.plotwidget.roi.size()[0], float(self.roi_size_y_le.text())]
        )

    def update_line_roi_start_x(self):
        pos1, pos2 = self.plotwidget.line_roi.get_pos()
        self.plotwidget.line_roi.set_pos(
            (float(self.line_roi_start_x_le.text()), pos1.y()), pos2
        )

    def update_line_roi_start_y(self):
        pos1, pos2 = self.plotwidget.line_roi.get_pos()
        self.plotwidget.line_roi.set_pos(
            (pos1.x(), float(self.line_roi_start_y_le.text())), pos2
        )

    def update_line_roi_end_x(self):
        pos1, pos2 = self.plotwidget.line_roi.get_pos()
        self.plotwidget.line_roi.set_pos(
            pos1, (float(self.line_roi_end_x_le.text()), pos2.y())
        )

    def update_line_roi_end_y(self):
        pos1, pos2 = self.plotwidget.line_roi.get_pos()
        self.plotwidget.line_roi.set_pos(
            pos1, (pos2.x(), float(self.line_roi_end_y_le.text()))
        )

    def update_line_roi_width(self):
        pos1, pos2 = self.plotwidget.line_roi.get_pos()
        self.plotwidget.line_roi.set_pos(
            pos1, pos2, float(self.line_roi_width_le.text())
        )

    def update_crosshair_roi_x(self):
        self.plotwidget.crosshair_roi.vertical_line.setValue(
            float(self.crosshair_roi_pos_x_le.text())
        )

    def update_crosshair_roi_y(self):
        self.plotwidget.crosshair_roi.horizontal_line.setValue(
            float(self.crosshair_roi_pos_y_le.text())
        )

    def toggle_log_mode(self, state):
        log_mode = state == Qt.Checked
        self.plotwidget.toggle_log_mode(log_mode)
        if self.disp_image is not None:
            self.plotwidget.update_image(force_image=self.disp_image)
        else:
            self.plotwidget.update_image()

    def single_shot_autoscale(self):
        self.plotwidget.autolevel_complete = False
        self.plotwidget.update_image(self.disp_image)

    def update_hist_max_level(self):
        hist_min, _ = self.plotwidget.image_item.getLevels()
        self.plotwidget.image_item.setLevels(
            [hist_min, float(self.hist_max_level_le.text())]
        )
        self.plotwidget.settings_histogram.item.imageChanged()

    def update_hist_min_level(self):
        _, hist_max = self.plotwidget.image_item.getLevels()
        self.plotwidget.image_item.setLevels(
            [float(self.hist_min_level_le.text()), hist_max]
        )
        self.plotwidget.settings_histogram.item.imageChanged()

    def roi_clicked(self):
        if self.plotwidget.image_view_controller.roi_cb.isChecked():
            self.plotwidget.show_roi()
        else:
            self.plotwidget.hide_roi()
        self.update_roi_view()

    def line_roi_clicked(self):
        if self.plotwidget.image_view_controller.line_roi_cb.isChecked():
            self.plotwidget.show_line_roi()
        else:
            self.plotwidget.hide_line_roi()
        self.update_roi_view()

    def roi_crosshair_clicked(self):
        if self.plotwidget.image_view_controller.roi_crosshair_cb.isChecked():
            self.plotwidget.show_crosshair_roi()
        else:
            self.plotwidget.hide_crosshair_roi()
        self.update_roi_view()

    def selector_roi_select_clicked(self):
        self.plotwidget.select_pixels = self.selector_roi_select_cb.isChecked()

    def selector_roi_display(self):
        pixel_dialog = PixelDialog(self.plotwidget.selected_pixels, parent=self)
        if pixel_dialog.exec_() == QDialog.Accepted:
            self.plotwidget.selected_pixels = pixel_dialog.selected_pixels
        self.update_selected_pixel_counter()

    def update_selected_pixel_counter(self):
        self.selector_roi_counter_label.setText(
            f"Selected Pixels: {len(self.plotwidget.selected_pixels)}"
        )

    def update_controller(self):
        self.update_selected_pixel_counter()

    def show_profile_clicked(self):
        if self.plotwidget.image_view_controller.profile_cb.isChecked():
            self.plotwidget.show_profiles()
        else:
            self.plotwidget.hide_profiles()
        self.update_roi_view()

    def update_roi_view(self):
        any_active = (
            self.plotwidget.image_view_controller.roi_cb.isChecked()
            or self.plotwidget.image_view_controller.roi_crosshair_cb.isChecked()
            or self.plotwidget.image_view_controller.line_roi_cb.isChecked()
            or self.plotwidget.image_view_controller.profile_cb.isChecked()
        )

        if any_active:
            self.plotwidget.show_roi_plotwidgets()
            # hide image axes so the linked side plots line up cleanly
            self.plotwidget.set_image_axes_visible(False)
        else:
            self.plotwidget.hide_roi_plotwidgets()
            # show image axes again when side plots are hidden
            self.plotwidget.set_image_axes_visible(True)
