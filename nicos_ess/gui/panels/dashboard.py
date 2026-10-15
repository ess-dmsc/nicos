# if sys.version_info < (3, 10):
#     from importlib_metadata import PackageNotFoundError, entry_points, version
# else:
#     from importlib.metadata import PackageNotFoundError, entry_points, version

import sys
from time import time as current_time

if sys.version_info < (3, 10):
    pass
else:
    pass


from nicos.clients.gui.data import DataHandler
from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import (
    loadUi,
)
from nicos.guisupport.colors import colors
from nicos.guisupport.qt import (
    QGridLayout,
    QLabel,
    QPixmap,
    QPushButton,
    QSizePolicy,
    Qt,
    QWidget,
    pyqtSlot,
)
from nicos.protocols.daemon import (
    STATUS_IDLE,
    STATUS_IDLEEXC,
    STATUS_INBREAK,
)
from nicos.utils import (
    findResource,
)
from nicos_ess.gui.utils import get_icon

try:
    from nicos.clients.gui.dialogs.help import HelpWindow
except ImportError:
    HelpWindow = None


class ToolbarItem:
    INSTRUMENT = {
        "name": "instrument",
        "location": "row_1",
        "label": "Instrument",
        "data_source": "session.instrument",
        "stringify": False,
        "upper_case": True,
    }
    EXPERIMENT = {
        "name": "experiment",
        "location": "row_1",
        "label": "     Experiment",
        "data_source": "session.experiment.title",
        "stringify": False,
    }
    PROPOSAL_ID = {
        "name": "proposal_ID",
        "location": "row_2",
        "label": "Proposal ID",
        "data_source": "session.experiment.proposal",
        "stringify": False,
    }
    RUN_NUMBER = {
        "name": "run_number",
        "location": "row_2",
        "label": "Run Number",
        "data_source": "session.experiment.get_current_run_number()",
        "stringify": True,
    }
    RUN_TITLE = {
        "name": "run_title",
        "location": "row_1",
        "label": "     Run Title",
        "data_source": "session.experiment.run_title",
        "stringify": False,
    }


ALL_TOOLBAR_ITEMS = [
    ToolbarItem.INSTRUMENT,
    ToolbarItem.PROPOSAL_ID,
    ToolbarItem.RUN_NUMBER,
    ToolbarItem.RUN_TITLE,
]


def decolor_logo(pixmap, color):
    ret_pix = QPixmap(pixmap.size())
    ret_pix.fill(color)
    ret_pix.setMask(pixmap.createMaskFromColor(Qt.GlobalColor.transparent))
    return ret_pix


class Spacer(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)


class StatusWidget(QWidget):
    @classmethod
    def _create_resources(cls):
        cls.status_icon = {
            "OK": get_icon("check_circle_green-24px.svg"),
            "OPEN": get_icon("check_circle_green-24px.svg"),
            "WARN": get_icon("warning_orange-24px.svg"),
            "BUSY": get_icon("sync_orange-24px.svg"),
            "NOTREACHED": get_icon("error-24px.svg"),
            "DISABLED": get_icon("not_interested-24px.svg"),
            "CLOSED": get_icon("not_interested-24px.svg"),
            "ERROR": get_icon("error-24px.svg"),
            "UNKNOWN": get_icon("device_unknown-24px.svg"),
        }

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.grid_layout = QGridLayout(self)
        self.setLayout(self.grid_layout)
        self.status_entries = {}
        self.maximum_status_columns = 3
        self.current_row = 0
        self.current_column = 0

        self._create_resources()

        # Example statuses
        # self.add_status(
        #     "Shutter Status", "shutter/status", "CLOSED", status_type="icon_text"
        # )
        # self.add_status("Proton Charge", "proton/charge", "0 µC", status_type="text")

        self.grid_layout.setColumnStretch(self.grid_layout.columnCount() + 1, 1)

    def add_status(self, label, key, initial_value, status_type="icon"):
        label_widget = QLabel(f"{label}:")
        label_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        label_widget.setStyleSheet("font-size: 17pt; font-weight: bold;")

        value_widget = QLabel(initial_value)
        value_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        value_widget.setStyleSheet("font-size: 17pt;")

        if self.current_column >= self.maximum_status_columns:
            self.current_row += 1
            self.current_column = 0

        col_base = self.current_column * 3

        icon_label = None
        self.grid_layout.addWidget(label_widget, self.current_row, col_base + 2)
        if status_type == "icon_text":
            icon_label = QLabel()
            icon_label.setPixmap(self.status_icon[initial_value].pixmap(24, 24))
            self.grid_layout.addWidget(icon_label, self.current_row, col_base + 1)
        else:
            self.grid_layout.addWidget(Spacer(), self.current_row, col_base + 1)
        self.grid_layout.addWidget(value_widget, self.current_row, col_base)

        entry = (label, value_widget, icon_label)
        self.status_entries[key] = entry

        self.current_column += 1


class Dashboard(Panel):
    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        colors.init_palette(self.palette())
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/dashboard.ui"))

        # state members
        self.current_status = None

        # connect client events
        self.client.connected.connect(self.on_client_connected)
        self.client.disconnected.connect(self.on_client_disconnected)
        self.client.status.connect(self.on_client_status)
        self.client.cache.connect(self.on_client_cache)
        self.client.experiment.connect(self._update_dashboard_info)

        # data handling setup
        self.data = DataHandler(self.client)

        # setting presets
        # TODO: Fix to work like in the mainWindow
        self.instrument = options.get("instrument")

        # build initial state
        self._init_dashboard()
        self.add_logo()
        # self.set_icons()
        self.actionEmergencyStop.setEnabled(self.client.isconnected)
        self._init_dashboard_labels(*ALL_TOOLBAR_ITEMS)
        self.add_status_widget()
        self.on_client_disconnected()

    def _init_dashboard(self):
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 17pt; font-weight: bold")
        self.status_text = QLabel()
        self.status_text.setStyleSheet("font-size: 17pt")
        self.emergency_button = QPushButton("STOP")
        self.emergency_button.setStyleSheet(
            "color:white; font-weight:bold; background-color: red; border-color:red"
        )

        self.dashboard = self.dashTopR
        self.dashboard.addWidget(
            self.status_label, Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignBottom
        )
        self.dashboard.addWidget(
            self.status_text, Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignBottom
        )
        self.dashboard.addWidget(
            self.emergency_button,
            Qt.AlignmentFlag.AlignRight,
            Qt.AlignmentFlag.AlignBottom,
        )

    def _init_dashboard_labels(self, *args):
        dashboardRow1 = self.leftRow1
        dashboardRow2 = self.leftRow2

        row_1_layout = dashboardRow1.layout()
        row_1_layout.setContentsMargins(0, 10, 0, 0)
        row_2_layout = dashboardRow2.layout()
        row_2_layout.setContentsMargins(0, 0, 0, 10)
        self.dashTopR.setContentsMargins(0, 0, 0, 10)

        for item in args:
            name = item.get("name")
            location = item.get("location")
            label, text = QLabel(), QLabel()
            label.setSizePolicy(
                QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred
            )
            text.setSizePolicy(
                QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred
            )
            if location == "row_1":
                label.setStyleSheet("font-size: 17pt; font-weight: bold")
                text.setStyleSheet("font-size: 17pt")
                dashboardRow1.addWidget(label)
                dashboardRow1.addWidget(text)
            elif location == "row_2":
                label.setStyleSheet("font-size: 14pt; font-weight: bold")
                text.setStyleSheet("font-size: 14pt")
                dashboardRow2.addWidget(label)
                dashboardRow2.addWidget(text)

            setattr(self, f"{name}_label", label)
            setattr(self, f"{name}_text", text)

        return

    def on_client_connected(self):
        self.setStatus("idle")
        self._reconnect_count = 0

        self.setTitlebar(True)
        # get all server status info
        initstatus = self.client.ask("getstatus")
        if initstatus:
            # handle initial status
            self.on_client_status(initstatus["status"])
            # propagate info to all components
            self.client.signal("initstatus", initstatus)

        self.emergency_button.setEnabled(not self.client.viewonly)

    def on_client_status(self, data):
        status = data[0]
        if status == STATUS_IDLE:
            self.setStatus("idle")
        elif status == STATUS_IDLEEXC:
            self.setStatus("idle", exception=True)
        elif status != STATUS_INBREAK:
            self.setStatus("running")
        else:
            self.setStatus("paused")

    def on_client_cache(self, data):
        return

    def on_client_disconnected(self):
        # self.setStatus("disconnected")
        self.emergency_button.setEnabled(False)
        self.setTitlebar(False)

    def setTitlebar(self, connected):
        inststr = str(self.instrument) or "NICOS"
        if connected:
            hoststr = f"{self.client.login} at {self.client.host}:{self.client.port}"
            self.setWindowTitle(f"{inststr} - {hoststr}")
        else:
            self.setWindowTitle(f"{inststr} - disconnected")

    def add_status_widget(self):
        self.status_widget = StatusWidget(self)
        self.dashTopR.addWidget(self.status_widget)

    def _update_dashboard_info(self):
        if self.current_status != "disconnected":
            self.update_text(*ALL_TOOLBAR_ITEMS)
        else:
            self.clear_label(*ALL_TOOLBAR_ITEMS)

    def clear_label(self, *args):
        for item in args:
            name = item.get("name")
            label = getattr(self, f"{name}_label")
            text = getattr(self, f"{name}_text")
            label.clear()
            text.clear()

    def _update_status_text(self):
        if self.current_status == "disconnected":
            self.status_label.setText(self.current_status.upper())
            self.status_text.setText("")
        else:
            self.status_label.setText("     NICOS Status: ")
            self.status_text.setText(self.current_status.upper())

    def update_text(self, *args):
        max_text_length = 50
        for item in args:
            name = item.get("name")

            label = getattr(self, f"{name}_label")
            text = getattr(self, f"{name}_text")

            value = self.client.eval(
                item.get("data_source", ""),
                None,
                stringify=item.get("stringify", False),
            )
            label.setText(f"{item.get('label', '')}:")

            if value:
                logo = decolor_logo(
                    QPixmap(f"{value}-logo"),
                    Qt.GlobalColor.white,
                )
                if logo.isNull():
                    if item.get("upper_case", False):
                        text.setText(value.upper()[0:max_text_length])
                    else:
                        text.setText(value[0:max_text_length])
                else:
                    text.setPixmap(
                        logo.scaledToHeight(
                            self.dashTop.height(),
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
            else:
                text.setText("UNKNOWN")

    def setStatus(self, status, exception=False):
        if status == self.current_status:
            return
        if (
            self.client.last_action_at
            and self.current_status == "running"
            and status in ("idle", "paused")
            and current_time() - self.client.last_action_at > 20
        ):
            self.client.last_action_at = 0
        self.current_status = status
        self._update_dashboard_info()
        self._update_status_text()

    def add_logo(self):

        nicos_label = QLabel()
        pxr = decolor_logo(
            QPixmap(":/nicos-logo-high"),
            Qt.GlobalColor.white,
        )
        nicos_label.setPixmap(
            pxr.scaledToHeight(30, Qt.TransformationMode.SmoothTransformation)
        )
        self.logo_box.addWidget(nicos_label)

    @pyqtSlot()
    def on_actionEmergencyStop_triggered(self):
        self.client.tell_action("emergency")
