# import traceback
# from time import strftime
# from time import time as current_time

# if sys.version_info < (3, 10):
#     from importlib_metadata import PackageNotFoundError, entry_points, version
# else:
#     from importlib.metadata import PackageNotFoundError, entry_points, version


# from contextlib import suppress

# import gr

# from nicos import nicos_version
# from nicos.clients.base import ConnectionData
# from nicos.clients.gui.client import NicosGuiClient
# from nicos.clients.gui.config import tabbed
# from nicos.clients.gui.data import DataHandler
# from nicos.clients.gui.dialogs.debug import DebugConsole
# from nicos.clients.gui.dialogs.error import ErrorDialog
# from nicos.clients.gui.dialogs.watchdog import WatchdogDialog
from nicos.clients.gui.panels import Panel  # , AuxiliaryWindow, createWindowItem

# from nicos.clients.gui.panels.console import ConsolePanel
# from nicos.clients.gui.tools import startStartupTools
from nicos.clients.gui.utils import (
    # DlgUtils,
    # SettingGroup,
    # dialogFromUi,
    # loadBasicWindowSettings,
    loadUi,
    # loadUserStyle,
)
from nicos.guisupport.colors import colors
from nicos.guisupport.qt import (
    # PYQT_VERSION_STR,
    # QT_VERSION_STR,
    # QAction,
    # QApplication,
    # QDialog,
    # QFontDialog,
    # QGridLayout,
    # QIcon,
    # QLabel,
    # QMainWindow,
    # QMenu,
    # QMessageBox,
    QPixmap,
    # QPoint,
    QSizePolicy,
    # QSystemTrayIcon,
    Qt,
    # QTimer,
    # QWebView,
    QWidget,
    # pyqtSignal,
    # pyqtSlot,
)

# from nicos.protocols.daemon import (
#     BREAK_NOW,
#     STATUS_IDLE,
#     STATUS_IDLEEXC,
#     STATUS_INBREAK,
# )
# from nicos.protocols.daemon.classic import DEFAULT_PORT
from nicos.utils import (
    # checkSetupSpec,
    findResource,
    # importString,
    # parseConnectionString,
)

# from nicos_ess.gui.dialogs.auth import ConnectionDialog
# from nicos_ess.gui.dialogs.settings import SettingsDialog
# from nicos_ess.gui.panels.setups import SetupsPanel
# from nicos_ess.gui.utils import get_icon

# try:
#     from nicos.clients.gui.dialogs.help import HelpWindow
# except ImportError:
#     HelpWindow = None


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


class Dashboard(Panel):
    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        colors.init_palette(self.palette())
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/dashboard.ui"))

        # create initial state
        self._init_dashboard()

    def _init_dashboard(self):
        self.setStyleSheet("background-color: #1f5366")

        self.label.setStyleSheet("font-size: 17pt; font-weight: bold")
