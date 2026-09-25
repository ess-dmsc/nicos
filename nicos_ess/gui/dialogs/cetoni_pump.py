from nicos.guisupport.qt import (
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
    QVBoxLayout,
    pyqtSignal,
)
from nicos_ess.gui.panels.parameters_table import ParametersTable
from nicos_ess.gui.panels.utils import attach_status_resources


class CetoniLinkedDialog(QDialog):
    """Dialog opened to control the Cetoni pumps running in linked pumping mode."""

    closed = pyqtSignal(object)

    def __init__(self, parent, devname, devinfo, devitem, log, expert):
        QDialog.__init__(self, parent)
        attach_status_resources(self)
        self.log = log

        # All executable commands go via the top-level devices panel
        self.devices_panel = parent
        self.client = parent.client
        self.devname = devname
        self.devinfo = devinfo
        self.devitem = devitem
        self.param_table = ParametersTable(
            parent, self.client, self.devname, self.devices_panel
        )
        self.setWindowTitle(f"Control {self.devname}")

        self.build_ui()

    def build_ui(self):
        self.create_widgets()
        self.set_layout()
        self.format_layout()

    def create_widgets(self):
        self.device_name = QLabel(f"Device: {self.devname}")
        self.device_description = QLabel("(description)")

        self.value_label = QLabel("Current value:")
        self.value_value = QLabel()
        self.status_label = QLabel("Status:")
        self.status_icon = QLabel()
        self.status_value = QLabel()

        self.mode_label = QLabel("Mode:")
        self.mode_value = QComboBox()
        self.time_label = QLabel("Time:")
        self.time_value = QLineEdit()
        self.time_unit = QLabel()
        self.first_fill_label = QLabel("First fill syringe")
        self.first_fill_value = QComboBox()
        self.flowrate_label = QLabel("Flowrate:")
        self.flowrate_value = QLineEdit()
        self.flowrate_unit = QLabel()
        self.vol_sp1_label = QLabel("Volume SP1:")
        self.vol_sp1_value = QLabel()
        self.vol_sp1_unit = QLabel()
        self.vol_sp2_label = QLabel("Volume SP2:")
        self.vol_sp2_value = QLabel()
        self.vol_sp2_unit = QLabel()
        self.vol_total_label = QLabel("Volume total:")
        self.vol_total_value = QLabel()
        self.vol_total_unit = QLabel()
        self.button_apply = QPushButton("Apply settings")

        self.button_more = QPushButton("More")
        self.button_reset = QPushButton("Reset")
        self.button_start = QPushButton("Start")
        self.button_stop = QPushButton("Stop")

        self.button_plot_hist = QPushButton("Plot history")
        self.button_show_params = QPushButton("Show parameters")
        self.button_close = QPushButton("Close")

    def set_layout(self):
        self.dialog_layout = QVBoxLayout()

        self.status_section = QVBoxLayout()
        self.value_status_grid = QGridLayout()
        self.value_status_grid.addWidget(self.value_label, 0, 0)
        self.value_status_grid.addWidget(self.value_value, 0, 2)
        self.value_status_grid.addWidget(self.status_label, 1, 0)
        self.value_status_grid.addWidget(self.status_icon, 1, 1)
        self.value_status_grid.addWidget(self.status_value, 1, 2)
        self.status_section.addWidget(self.device_name)
        self.status_section.addWidget(self.device_description)
        self.status_section.addSpacing(6)
        self.status_section.addLayout(self.value_status_grid)

        self.settings_group = QGroupBox("Settings", self)
        self.settings_section = QVBoxLayout()
        self.settings_grid = QGridLayout()
        self.settings_grid.addWidget(self.mode_label, 0, 0)
        self.settings_grid.addWidget(
            self.mode_value,
            0,
            1,
        )
        self.settings_grid.addWidget(self.time_label, 1, 0)
        self.settings_grid.addWidget(self.time_value, 1, 1)
        self.settings_grid.addWidget(self.time_unit, 1, 2)
        self.settings_grid.addWidget(self.first_fill_label, 2, 0)
        self.settings_grid.addWidget(self.first_fill_value, 2, 1)
        self.settings_grid.addWidget(self.flowrate_label, 3, 0)
        self.settings_grid.addWidget(self.flowrate_value, 3, 1)
        self.settings_grid.addWidget(self.flowrate_unit, 3, 2)
        self.settings_grid.addWidget(self.vol_sp1_label, 4, 0)
        self.settings_grid.addWidget(self.vol_sp1_value, 4, 1)
        self.settings_grid.addWidget(self.vol_sp1_unit, 4, 2)
        self.settings_grid.addWidget(self.vol_sp2_label, 5, 0)
        self.settings_grid.addWidget(self.vol_sp2_value, 5, 1)
        self.settings_grid.addWidget(self.vol_sp2_unit, 5, 2)
        self.settings_grid.addWidget(self.vol_total_label, 6, 0)
        self.settings_grid.addWidget(self.vol_total_value, 6, 1)
        self.settings_grid.addWidget(self.vol_total_unit, 6, 2)
        self.settings_section.addLayout(self.settings_grid)
        self.settings_section.addWidget(
            self.button_apply, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.settings_group.setLayout(self.settings_section)

        self.controls_section = QHBoxLayout()
        self.controls_section.addWidget(self.button_more)
        self.controls_section.addWidget(self.button_reset)
        self.controls_section.addStretch()
        self.controls_section.addWidget(self.button_start)
        self.controls_section.addWidget(self.button_stop)

        self.bottom_section = QHBoxLayout()
        self.bottom_section.addWidget(self.button_plot_hist)
        self.bottom_section.addWidget(self.button_show_params)
        self.bottom_section.addStretch()
        self.bottom_section.addWidget(self.button_close)

        self.dialog_layout.addLayout(self.status_section)
        self.dialog_layout.addSpacing(14)
        self.dialog_layout.addWidget(self.settings_group)
        self.dialog_layout.addSpacing(14)
        self.dialog_layout.addLayout(self.controls_section)
        self.dialog_layout.addSpacing(14)
        self.dialog_layout.addLayout(self.bottom_section)
        self.setLayout(self.dialog_layout)

    def format_layout(self):
        VALUE_FIELD_WIDTH = 120
        UNIT_FIELD_WIDTH = 25
        ROW_HEIGHT = 24

        value_fields = [
            self.mode_value,
            self.time_value,
            self.first_fill_value,
            self.flowrate_value,
            self.vol_sp1_value,
            self.vol_sp2_value,
            self.vol_sp2_value,
            self.vol_total_value,
        ]

        unit_fields = [
            self.time_unit,
            self.flowrate_unit,
            self.vol_sp1_unit,
            self.vol_sp2_unit,
            self.vol_total_unit,
        ]

        for widget in value_fields:
            widget.setMaximumWidth(VALUE_FIELD_WIDTH)

        for widget in unit_fields:
            widget.setMaximumWidth(UNIT_FIELD_WIDTH)

        for row in range(self.settings_grid.rowCount()):
            self.settings_grid.setRowMinimumHeight(row, ROW_HEIGHT)
