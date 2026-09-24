from nicos.guisupport.qt import (
    QComboBox,
    QDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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

        # widgets
        self.dialog_layout = QVBoxLayout()

        ## status section
        self.device_status_section = QVBoxLayout()
        self.device_name = QLabel(f"Device: {self.devname}")
        self.device_description = QLabel("(description)")

        self.value_status_grid = QGridLayout()
        self.value_label = QLabel("Current value:")
        self.value_value = QLabel()
        self.status_label = QLabel("Status:")
        self.status_icon = QLabel()
        self.status_value = QLabel()
        self.value_status_grid.addWidget(self.value_label, 0, 0)
        self.value_status_grid.addWidget(self.value_value, 0, 2)
        self.value_status_grid.addWidget(self.status_label, 1, 0)
        self.value_status_grid.addWidget(self.status_icon, 1, 1)
        self.value_status_grid.addWidget(self.status_value, 1, 2)

        self.device_status_section.addWidget(self.device_name)
        self.device_status_section.addWidget(self.device_description)
        self.device_status_section.addLayout(self.value_status_grid)

        ## control section
        self.control_section = QVBoxLayout()
        self.control_header = QLabel()
        self.control_grid = QGridLayout()
        self.mode_label = QLabel("Mode:")
        self.mode_value = QLineEdit()
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
        self.button_start = QPushButton("Start")

        self.control_grid.addWidget(self.mode_label, 0, 0)
        self.control_grid.addWidget(self.mode_value, 0, 1)
        self.control_grid.addWidget(self.time_label, 1, 0)
        self.control_grid.addWidget(self.time_value, 1, 1)
        self.control_grid.addWidget(self.time_unit, 1, 2)
        self.control_grid.addWidget(self.first_fill_label, 2, 0)
        self.control_grid.addWidget(self.first_fill_value, 2, 1)
        self.control_grid.addWidget(self.flowrate_label, 3, 0)
        self.control_grid.addWidget(self.flowrate_value, 3, 1)
        self.control_grid.addWidget(self.flowrate_unit, 3, 2)
        self.control_grid.addWidget(self.vol_sp1_label, 4, 0)
        self.control_grid.addWidget(self.vol_sp1_value, 4, 1)
        self.control_grid.addWidget(self.vol_sp1_unit, 4, 2)
        self.control_grid.addWidget(self.vol_sp2_label, 5, 0)
        self.control_grid.addWidget(self.vol_sp2_value, 5, 1)
        self.control_grid.addWidget(self.vol_sp2_unit, 5, 2)
        self.control_grid.addWidget(self.vol_total_label, 6, 0)
        self.control_grid.addWidget(self.vol_total_value, 6, 1)
        self.control_grid.addWidget(self.vol_total_unit, 6, 2)
        self.control_grid.addWidget(self.button_start, 7, 1)

        self.control_section.addWidget(self.control_header)
        self.control_section.addLayout(self.control_grid)

        self.dialog_layout.addLayout(self.device_status_section)
        self.dialog_layout.addLayout(self.control_section)
        self.setLayout(self.dialog_layout)
