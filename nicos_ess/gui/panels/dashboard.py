from time import time as current_time

from nicos.clients.gui.data import DataHandler
from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import (
    loadUi,
)
from nicos.guisupport.colors import colors
from nicos.guisupport.qt import (
    QLabel,
    QPixmap,
    QPushButton,
    QSizePolicy,
    Qt,
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


class DashboardItem:
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
        "location": "col_l",
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
        "label": "     Run Number",
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


ALL_DASHBOARD_ITEMS = [
    DashboardItem.INSTRUMENT,
    DashboardItem.PROPOSAL_ID,
    DashboardItem.RUN_NUMBER,
    DashboardItem.RUN_TITLE,
    # DashboardItem.EXPERIMENT,
]


def decolor_logo(pixmap, color):
    ret_pix = QPixmap(pixmap.size())
    ret_pix.fill(color)
    ret_pix.setMask(pixmap.createMaskFromColor(Qt.GlobalColor.transparent))
    return ret_pix


class Dashboard(Panel):
    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        colors.init_palette(self.palette())
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/dashboard.ui"))
        # state members
        self.current_status = None
        self.gui_conf = parent.gui_conf

        # connect client events
        self.client.connected.connect(self.on_client_connected)
        self.client.disconnected.connect(self.on_client_disconnected)
        self.client.status.connect(self.on_client_status)
        self.client.cache.connect(self.on_client_cache)
        self.client.experiment.connect(self._update_dashboard_info)

        # data handling setup
        self.data = DataHandler(self.client)

        # setting presets
        self.instrument = self.gui_conf.name

        # build initial state
        self._init_dashboard()
        self.add_logo()
        self.actionEmergencyStop.setEnabled(self.client.isconnected)
        self._init_dashboard_labels(*ALL_DASHBOARD_ITEMS)
        self.on_client_disconnected()

    def _init_dashboard(self):
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 17pt; font-weight: bold")
        self.status_text = QLabel()
        self.status_text.setStyleSheet("font-size: 17pt")

        self.emergency_button = QPushButton("STOP")
        self.emergency_button.clicked.connect(self.on_actionEmergencyStop_triggered)
        self.emergency_button.setProperty("class", "stopButton")
        self.login_button = QPushButton("Logout")
        self.login_button.clicked.connect(self.on_actionLogin_triggered)
        self.login_button.setProperty("class", "loginButton")

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
        self.dashboard.addWidget(
            self.login_button,
            Qt.AlignmentFlag.AlignRight,
            Qt.AlignmentFlag.AlignBottom,
        )

    def on_actionLogin_triggered(self):
        self.parent.actionConnect.trigger()

    def _init_dashboard_labels(self, *args):
        dashboardRow1 = self.leftRow1
        dashboardRow2 = self.leftRow2
        dashboardRow2.setContentsMargins(0, 0, 0, 10)

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
            elif location == "col_l":
                label.setStyleSheet("font-size: 14pt; font-weight: bold")
                text.setStyleSheet("font-size: 14pt")
                self.dashLeft.addWidget(label)
                self.dashLeft.addWidget(text)

            setattr(self, f"{name}_label", label)
            setattr(self, f"{name}_text", text)

        return

    def on_client_connected(self):
        self.setStatus("idle   ")
        self._reconnect_count = 0

        # get all server status info
        initstatus = self.client.ask("getstatus")
        if initstatus:
            # handle initial status
            self.on_client_status(initstatus["status"])
            # propagate info to all components
            self.client.signal("initstatus", initstatus)

        self.emergency_button.setEnabled(not self.client.viewonly)
        self.login_button.setText("Logout")
        self.login_button.setIcon(get_icon("power_off-24px.svg"))

    def on_client_status(self, data):
        status = data[0]
        if status == STATUS_IDLE:
            self.setStatus("idle   ")
        elif status == STATUS_IDLEEXC:
            self.setStatus("idle   ", exception=True)
        elif status != STATUS_INBREAK:
            self.setStatus("running   ")
        else:
            self.setStatus("paused   ")

    def on_client_cache(self, data):
        pass

    def on_client_disconnected(self):
        self.setStatus("disconnected")
        self.emergency_button.setEnabled(False)
        self.login_button.setIcon(get_icon("power-24px.svg"))
        self.login_button.setText("Login")

    def _update_dashboard_info(self):
        if self.current_status != "disconnected":
            self.update_text(*ALL_DASHBOARD_ITEMS)
        else:
            self.clear_label(*ALL_DASHBOARD_ITEMS)

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
            self.status_label.setText("     NICOS Status:")
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

            if value is not None:
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
