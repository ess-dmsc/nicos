# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Georg Brandl <g.brandl@fz-juelich.de>
#   Christian Felder <c.felder@fz-juelich.de>
#   Michele Brambilla <michele.brambilla@psi.ch>
#
# *****************************************************************************

"""NICOS GUI main window."""

import sys
import traceback
from os import path
from time import strftime, time as current_time

import gr

from nicos import nicos_version
from nicos.clients.base import ConnectionData
from nicos.clients.gui.client import NicosGuiClient
from nicos.clients.gui.config import tabbed
from nicos.clients.gui.data import DataHandler
from nicos.clients.gui.dialogs.debug import DebugConsole
from nicos.clients.gui.dialogs.error import ErrorDialog
from nicos.clients.gui.dialogs.pnp import PnPSetupQuestion
from nicos.clients.gui.dialogs.watchdog import WatchdogDialog
from nicos.clients.gui.panels import AuxiliaryWindow, createWindowItem
from nicos.clients.gui.panels.console import ConsolePanel
from nicos.clients.gui.tools import startStartupTools
from nicos.clients.gui.utils import (
    DlgUtils,
    SettingGroup,
    dialogFromUi,
    loadBasicWindowSettings,
    loadUi,
    loadUserStyle,
)
from nicos.core.utils import ADMIN
from nicos.guisupport.colors import colors
from nicos.guisupport.qt import (
    PYQT_VERSION_STR,
    QT_VERSION_STR,
    QAction,
    QApplication,
    QColorDialog,
    QDialog,
    QFontDialog,
    QGridLayout,
    QIcon,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPixmap,
    QPoint,
    QSizePolicy,
    QSystemTrayIcon,
    Qt,
    QTimer,
    QWebView,
    QWidget,
    pyqtSignal,
    pyqtSlot,
)
from nicos.protocols.daemon import (
    BREAK_NOW,
    STATUS_IDLE,
    STATUS_IDLEEXC,
    STATUS_INBREAK,
)
from nicos.protocols.daemon.classic import DEFAULT_PORT
from nicos.utils import (
    checkSetupSpec,
    findResource,
    importString,
    parseConnectionString,
)

from nicos_ess.gui.dialogs.auth import ConnectionDialog
from nicos_ess.gui.dialogs.settings import SettingsDialog
from nicos_ess.gui.utils import get_icon, root_path

try:
    from nicos.clients.gui.dialogs.help import HelpWindow
except ImportError:
    HelpWindow = None


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
        # self.add_status("Shutter Status", 'shutter/status', 'CLOSED', status_type='icon_text')
        # self.add_status("Proton Charge", 'proton/charge', '0 µC', status_type='text')

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

    def update_status(self, data):
        """
        Method that is called when the cache signal is emitted from the client.
        Use to update the status of the widgets.
        """
        ts, key, ttl, value = data


class ToolAction(QAction):
    """Extended QAction which is setup depending visible.

    The action is visible if no special setup is configured or the loaded setup
    matches the ``setups`` rule.
    """

    def __init__(self, client, icon, text, options, parent=None):
        QAction.__init__(self, icon, text, parent)
        # the default menu rule is TextHeuristicRole, which moves 'setup' to
        # the 'Preferences' Menu on a Mac -> this is not what we want
        self.setMenuRole(self.MenuRole.NoRole)
        setups = options.get("setups", "")
        self.setupSpec = setups
        if self.setupSpec:
            client.register(self, "session/mastersetup")

    def on_keyChange(self, key, value, time, expired):
        if key == "session/mastersetup" and self.setupSpec:
            self.setVisible(checkSetupSpec(self.setupSpec, value))


class MainWindow(DlgUtils, QMainWindow):
    name = "MainWindow"
    # Emitted when a panel generates code that an editor panel should add.
    codeGenerated = pyqtSignal(object)

    # Interval (in ms) to make "keepalive" queries to the daemon.
    keepaliveInterval = 12 * 3600 * 1000

    default_facility_logo = ":/ess-logo-auth"

    def __init__(
        self, log, gui_conf, viewonly=False, default_server=None, default_user=None
    ):
        QMainWindow.__init__(self)
        DlgUtils.__init__(self, "NICOS")
        colors.init_palette(self.palette())
        loadUi(self, findResource("nicos_ess/gui/main.ui"))

        # set app icon in multiple sizes
        icon = QIcon()
        icon.addFile(":/appicon")
        icon.addFile(":/appicon-16")
        icon.addFile(":/appicon-48")
        QApplication.setWindowIcon(icon)

        # hide admin label until we are connected as admin
        self.adminLabel.hide()

        # our logger instance
        self.log = log

        # window for displaying errors
        self.errorWindow = None

        # window for "prompt" event confirmation
        self.promptWindow = None

        # debug console window, if opened
        self.debugConsole = None

        # log messages sent by the server
        self.messages = []

        # are we in expert mode?  (always false on startup)
        self.expertmode = False

        # no wrapping at startup
        self.allowoutputlinewrap = False

        # default server to connect to
        self.default_server = default_server

        # default user to suggest
        self.default_user = default_user

        # set up the initial connection data
        self.setConnData(
            ConnectionData("localhost", 1301, "guest", None, viewonly=viewonly)
        )

        # state members
        self.current_status = None

        self.style_file = gui_conf.stylefile

        # connect the client's events
        self.client = NicosGuiClient(self, self.log)
        self.client.error.connect(self.on_client_error)
        self.client.broken.connect(self.on_client_broken)
        self.client.failed.connect(self.on_client_failed)
        self.client.connected.connect(self.on_client_connected)
        self.client.disconnected.connect(self.on_client_disconnected)
        self.client.status.connect(self.on_client_status)
        self.client.cache.connect(self.on_client_cache)
        self.client.showhelp.connect(self.on_client_showhelp)
        self.client.clientexec.connect(self.on_client_clientexec)
        self.client.plugplay.connect(self.on_client_plugplay)
        self.client.watchdog.connect(self.on_client_watchdog)
        self.client.prompt.connect(self.on_client_prompt)
        self.client.experiment.connect(self._update_toolbar_info)

        # data handling setup
        self.data = DataHandler(self.client)

        # panel configuration
        self.gui_conf = gui_conf
        self.facility_logo = gui_conf.options.get(
            "facility_logo", self.default_facility_logo
        )
        self.initDataReaders()
        self.mainwindow = self

        # determine if there is an editor window type, because we would like to
        # have a way to open files from a console panel later
        self.editor_wintype = self.gui_conf.find_panel(
            ("editor.EditorPanel", "nicos_ess.gui.panels.editor.EditorPanel")
        )
        self.history_wintype = self.gui_conf.find_panel(
            ("history.HistoryPanel", "nicos_ess.gui.panels.history.HistoryPanel")
        )

        # additional panels
        self.panels = []
        self.splitters = []
        self.windowtypes = []
        self.windows = {}

        # setting presets
        self.instrument = self.gui_conf.name

        self.createWindowContent()

        # timer for reconnecting
        self.reconnectTimer = QTimer(singleShot=True, timeout=self._reconnect)
        self._reconnect_count = 0
        self._reconnect_time = 0

        # timer for session keepalive, every 12 hours
        self.keepaliveTimer = QTimer(singleShot=False, timeout=self._keepalive)
        self.keepaliveTimer.start(self.keepaliveInterval)

        # setup tray icon
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.activated.connect(self.on_trayIcon_activated)
        self.trayMenu = QMenu(self)
        nameAction = self.trayMenu.addAction(self.instrument)
        nameAction.setEnabled(False)
        self.trayMenu.addSeparator()
        toggleAction = self.trayMenu.addAction("Hide main window")
        toggleAction.setCheckable(True)
        toggleAction.triggered[bool].connect(lambda hide: self.setVisible(not hide))
        self.trayIcon.setContextMenu(self.trayMenu)

        # help window
        self.helpWindow = None
        # watchdog window
        self.watchdogWindow = None
        # plug-n-play notification windows
        self.pnpWindows = {}

        # create initial state
        self._init_toolbar()
        self.add_logo()
        self.set_icons()
        self._create_cheeseburger_menu()
        self.actionUser.setIconVisibleInMenu(True)
        self.actionExpert.setEnabled(self.client.isconnected)
        self.actionEmergencyStop.setEnabled(self.client.isconnected)
        self._init_instrument_name()
        self._init_experiment_name()
        self.add_status_widget()
        self.on_client_disconnected()

    def _create_cheeseburger_menu(self):
        dropdown = QMenu("")
        dropdown.addAction(self.actionConnect)
        dropdown.addAction(self.actionViewOnly)
        dropdown.addAction(self.actionPreferences)
        dropdown.addAction(self.actionExpert)
        dropdown.addSeparator()
        dropdown.addAction(self.actionExit)
        self.dropdown = dropdown

    def _init_toolbar(self):
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 17pt; font-weight: bold")
        self.status_text = QLabel()
        self.status_text.setStyleSheet("font-size: 17pt")

        self.toolbar = self.toolBarRight
        self.toolbar.addWidget(self.status_text)
        self.toolbar.addWidget(self.status_label)

    def _init_experiment_name(self):
        self.experiment_label = QLabel()
        self.experiment_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.experiment_label.setStyleSheet("font-size: 17pt; " "font-weight: bold")
        self.toolBarMain.addWidget(self.experiment_label)

        self.experiment_text = QLabel()
        self.experiment_text.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.experiment_text.setStyleSheet("font-size: 17pt")
        self.toolBarMain.addWidget(self.experiment_text)

    def _init_instrument_name(self):
        self.instrument_label = QLabel()
        self.instrument_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.instrument_label.setStyleSheet("font-size: 17pt; " "font-weight: bold")
        self.toolBarMain.addWidget(self.instrument_label)

        self.instrument_text = QLabel()
        self.instrument_text.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.instrument_text.setStyleSheet("font-size: 17pt")
        self.toolBarMain.addWidget(self.instrument_text)

    def set_icons(self):
        self.actionUser.setIcon(get_icon("settings_applications-24px.svg"))
        self.actionEmergencyStop.setIcon(get_icon("emergency_stop_cross_red-24px.svg"))
        self.actionConnect.setIcon(get_icon("power-24px.svg"))
        self.actionExit.setIcon(get_icon("exit_to_app-24px.svg"))
        self.actionViewOnly.setIcon(get_icon("lock-24px.svg"))
        self.actionPreferences.setIcon(get_icon("tune-24px.svg"))
        self.actionExpert.setIcon(get_icon("fingerprint-24px.svg"))

    def add_logo(self):
        spacer = QWidget()
        spacer.setMinimumWidth(20)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.toolBarMain.insertWidget(self.toolBarMain.actions()[0], spacer)

        nicos_label = QLabel()
        pxr = decolor_logo(
            QPixmap(path.join(root_path, "resources", "nicos-logo-high.svg")),
            Qt.GlobalColor.white,
        )
        nicos_label.setPixmap(
            pxr.scaledToHeight(
                self.toolBarMain.height(), Qt.TransformationMode.SmoothTransformation
            )
        )
        self.toolBarMain.insertWidget(self.toolBarMain.actions()[1], nicos_label)

    def add_status_widget(self):
        self.status_widget = StatusWidget(self)
        self.toolBarRight.addWidget(self.status_widget)

    def update_instrument_text(self):
        instrument = self.client.eval("session.instrument", None)
        self.instrument_label.setText("Instrument:")
        if instrument:
            logo = decolor_logo(
                QPixmap(path.join(root_path, "resources", f"{instrument}-logo.svg")),
                Qt.GlobalColor.white,
            )
            if logo.isNull():
                self.instrument_text.setText(instrument.upper())
                return
            self.instrument_text.setPixmap(
                logo.scaledToHeight(
                    self.toolBarMain.height(),
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.instrument_text.setText("UNKNOWN")

    def update_experiment_text(self):
        max_text_length = 50
        experiment = self.client.eval("session.experiment.title", None)
        if experiment is not None:
            self.experiment_label.setText("     Experiment:")
            self.experiment_text.setText(experiment[0:max_text_length])

    @staticmethod
    def setQSS(style_file):
        with open(style_file, "r", encoding="utf-8") as fd:
            try:
                QApplication.instance().setStyleSheet(fd.read())
            except Exception as e:
                print(e)

    def _update_toolbar_info(self):
        if self.current_status != "disconnected":
            self.update_instrument_text()
            self.update_experiment_text()
        else:
            self.clear_experiment_text()
            self.clear_instrument_text()

    def _update_status_text(self):
        if self.current_status == "disconnected":
            self.status_label.setText(self.current_status.upper())
            self.status_text.setText("")
        else:
            self.status_label.setText("     Status: ")
            self.status_text.setText(self.current_status.upper())

    def clear_instrument_text(self):
        self.instrument_label.clear()
        self.instrument_text.clear()

    def clear_experiment_text(self):
        self.experiment_label.clear()
        self.experiment_text.clear()

    def addPanel(self, panel, always=True):
        if always or panel not in self.panels:
            self.panels.append(panel)

    def createWindowContent(self):
        self.sgroup = SettingGroup("MainWindow")
        with self.sgroup as settings:
            loadUserStyle(self, settings)
            # load saved settings and stored layout for panel config
            self.loadSettings(settings)

        # create panels in the main window
        widget = createWindowItem(self.gui_conf.main_window, self, self, self, self.log)
        if widget:
            self.centralLayout.addWidget(widget)
        self.centralLayout.setContentsMargins(0, 0, 0, 0)

        # call postInit after creation of all panels
        for panel in self.panels:
            panel.postInit()

        with self.sgroup as settings:
            # geometry and window appearance
            loadBasicWindowSettings(self, settings)
            self.update()
            # load auxiliary windows state
            self.loadAuxWindows(settings)
        if len(self.splitstate) == len(self.splitters):
            for sp, st in zip(self.splitters, self.splitstate):
                sp.restoreState(st)

        if not self.gui_conf.windows:
            self.menuBar().removeAction(self.menuWindows.menuAction())
        for i, wconfig in enumerate(self.gui_conf.windows):
            action = ToolAction(
                self.client,
                QIcon(":/" + wconfig.icon),
                wconfig.name,
                wconfig.options,
                self,
            )
            self.toolBarWindows.addAction(action)
            self.menuWindows.addAction(action)

            def window_callback(on, i=i):
                self.createWindow(i)

            action.triggered[bool].connect(window_callback)
        if not self.gui_conf.windows:
            self.toolBarWindows.hide()
        else:
            self.toolBarWindows.show()

        if isinstance(self.gui_conf.main_window, tabbed) and widget:
            widget.tabChangedTab(0)

    def createWindow(self, wtype):
        # for the history_wintype or editor_wintype
        if wtype == -1:
            return self
        try:
            wconfig = self.gui_conf.windows[wtype]
        except IndexError:
            # config outdated, window type doesn't exist
            return
        if wtype in self.windows:
            window = self.windows[wtype]
            window.activateWindow()
            return window
        window = AuxiliaryWindow(self, wtype, wconfig)
        if window.centralLayout.count():
            window.setWindowIcon(QIcon(":/" + wconfig.icon))
            self.windows[wtype] = window
            window.closed.connect(self.on_auxWindow_closed)
            for panel in window.panels:
                panel.updateStatus(self.current_status)
            window.show()
            return window
        else:
            del window
            return None

    def getPanel(self, panelName):
        for panelobj in self.panels:
            if panelobj.panelName == panelName:
                return panelobj

    def initDataReaders(self):
        try:
            # just import to register all default readers
            # pylint: disable=unused-import
            import nicos.devices.datasinks
        except ImportError:
            pass
        classes = self.gui_conf.options.get("reader_classes", [])
        for clsname in classes:
            try:
                importString(clsname)
            except ImportError:
                pass

    def on_auxWindow_closed(self, window):
        del self.windows[window.type]
        window.deleteLater()

    def setConnData(self, data):
        self.conndata = data

    def _reconnect(self):
        if self._reconnect_count and self.conndata.password is not None:
            self._reconnect_count -= 1
            if self._reconnect_count <= self.client.RECONNECT_TRIES_LONG:
                self._reconnect_time = self.client.RECONNECT_INTERVAL_LONG
            self.client.connect(self.conndata)

    def _keepalive(self):
        if self.client.isconnected:
            self.client.ask("keepalive")

    def show(self):
        QMainWindow.show(self)
        if self.autoconnect and not self.client.isconnected:
            self.on_actionConnect_triggered(True)
        if sys.platform == "darwin":
            # on Mac OS loadBasicWindowSettings seems not to work before show()
            # so we do it here again
            with self.sgroup as settings:
                loadBasicWindowSettings(self, settings)

    def startup(self):
        self.show()
        startStartupTools(self, self.gui_conf.tools)

    def loadSettings(self, settings):
        self.autoconnect = settings.value("autoconnect", True, bool)

        self.connpresets = {}
        # new setting key, with dictionary values
        for k, v in settings.value("connpresets_new", {}).items():
            self.connpresets[k] = ConnectionData(**v).copy()
        # if it was empty, try old setting key with list values
        if not self.connpresets:
            for k, v in settings.value("connpresets", {}).items():
                self.connpresets[k] = ConnectionData(
                    host=v[0], port=int(v[1]), user=v[2], password=None
                )
        # if there are presets defined in the gui config add them and override
        # existing ones
        for key, connection in self.gui_conf.options.get(
            "connection_presets", {}
        ).items():
            parsed = parseConnectionString(connection, DEFAULT_PORT)
            if parsed:
                parsed["viewonly"] = True
                if key not in self.connpresets:
                    self.connpresets[key] = ConnectionData(**parsed)
                else:  # reset only host if connection is already configured
                    self.connpresets[key].host = parsed["host"]

        self.lastpreset = settings.value("lastpreset", "")
        if self.lastpreset in self.connpresets:
            self.setConnData(self.connpresets[self.lastpreset])

        self.instrument = settings.value("instrument", self.gui_conf.name)
        self.confirmexit = settings.value("confirmexit", True, bool)
        self.warnwhenadmin = settings.value("warnwhenadmin", True, bool)
        self.showtrayicon = settings.value("showtrayicon", True, bool)
        self.autoreconnect = settings.value("autoreconnect", True, bool)
        self.autosavelayout = settings.value("autosavelayout", True, bool)
        self.allowoutputlinewrap = settings.value("allowoutputlinewrap", False, bool)
        self.update()

    def loadAuxWindows(self, settings):
        open_wintypes = settings.value("auxwindows") or []
        if isinstance(open_wintypes, str):
            open_wintypes = [int(w) for w in open_wintypes.split(",")]

        for wtype in open_wintypes:
            if isinstance(wtype, str):
                wtype = int(wtype)
            self.createWindow(wtype)

    def saveWindowLayout(self):
        with self.sgroup as settings:
            settings.setValue("geometry", self.saveGeometry())
            settings.setValue("windowstate", self.saveState())
            settings.setValue("splitstate", [sp.saveState() for sp in self.splitters])
            open_wintypes = list(self.windows)
            settings.setValue("auxwindows", open_wintypes)

    def saveSettings(self, settings):
        settings.setValue("autoconnect", self.client.isconnected)
        settings.setValue(
            "connpresets_new", {k: v.serialize() for (k, v) in self.connpresets.items()}
        )
        settings.setValue("lastpreset", self.lastpreset)
        settings.setValue("font", self.user_font)
        settings.setValue("color", self.user_color)

    def closeEvent(self, event):
        if (
            self.confirmexit
            and QMessageBox.question(self, "Quit", "Do you really want to quit?")
            == QMessageBox.StandardButton.No
        ):
            event.ignore()
            return

        for panel in self.panels:
            if not panel.requestClose():
                event.ignore()
                return

        if self.autosavelayout:
            self.saveWindowLayout()
        with self.sgroup as settings:
            self.saveSettings(settings)
        for panel in self.panels:
            with panel.sgroup as settings:
                panel.saveSettings(settings)

        for window in list(self.windows.values()):
            if not window.close():
                event.ignore()
                return

        if self.helpWindow:
            self.helpWindow.close()

        if self.client.isconnected:
            self.on_actionConnect_triggered(False)

        event.accept()
        QApplication.instance().quit()

    def setTitlebar(self, connected):
        inststr = str(self.instrument) or "NICOS"
        if connected:
            hoststr = "%s at %s:%s" % (
                self.client.login,
                self.client.host,
                self.client.port,
            )
            self.setWindowTitle("%s - %s" % (inststr, hoststr))
        else:
            self.setWindowTitle("%s - disconnected" % inststr)

    def setStatus(self, status, exception=False):
        if status == self.current_status:
            return
        if (
            self.client.last_action_at
            and self.current_status == "running"
            and status in ("idle", "paused")
            and current_time() - self.client.last_action_at > 20
        ):
            # show a visual indication of what happened
            if status == "paused":
                msg = "Script is now paused."
            elif exception:
                msg = "Script has exited with an error."
            else:
                msg = "Script has finished."
            self.trayIcon.showMessage(self.instrument, msg)
            self.client.last_action_at = 0
        self.current_status = status
        self._update_toolbar_info()
        self._update_status_text()
        # new status icon
        pixmap = QPixmap(":/" + status + ("exc" if exception else ""))
        new_icon = QIcon()
        new_icon.addPixmap(pixmap, QIcon.Mode.Disabled)
        self.trayIcon.setIcon(new_icon)
        self.trayIcon.setToolTip("%s status: %s" % (self.instrument, status))
        if self.showtrayicon:
            self.trayIcon.show()
        if self.promptWindow and status != "paused":
            self.promptWindow.close()
        # propagate to panels
        for panel in self.panels:
            panel.updateStatus(status, exception)
        for window in self.windows.values():
            for panel in window.panels:
                panel.updateStatus(status, exception)

    def on_client_error(self, problem, exc=None):
        if exc is not None:
            self.log.error("Error from daemon", exc=exc)
        problem = strftime("[%m-%d %H:%M:%S] ") + problem
        if self.errorWindow is None:

            def reset_errorWindow():
                self.errorWindow = None

            self.errorWindow = ErrorDialog(self, windowTitle="Daemon error")
            self.errorWindow.accepted.connect(reset_errorWindow)
            self.errorWindow.addMessage(problem)
            self.errorWindow.show()
        else:
            self.errorWindow.addMessage(problem)

    def on_client_broken(self, problem):
        self.on_client_error(problem)
        if self.autoreconnect:
            self._reconnect_count = self.client.RECONNECT_TRIES
            self._reconnect_time = self.client.RECONNECT_INTERVAL_SHORT
            self.reconnectTimer.start(self._reconnect_time)

    def on_client_failed(self, problem):
        if self._reconnect_count:
            self.reconnectTimer.start(self._reconnect_time)
        else:
            self.on_client_error(problem)

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

        # show warning label for admin users
        self.adminLabel.setVisible(
            self.warnwhenadmin
            and self.client.user_level is not None
            and self.client.user_level >= ADMIN
        )

        self.actionConnect.setIcon(get_icon("power_off-24px.svg"))
        self.actionExpert.setEnabled(True)
        self.actionViewOnly.setEnabled(True)
        self.actionEmergencyStop.setEnabled(not self.client.viewonly)
        self.actionConnect.setText("Disconnect")

        # set focus to command input, if present
        for panel in self.panels:
            if isinstance(panel, ConsolePanel) and panel.hasinput:
                panel.commandInput.setFocus()

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
        self.status_widget.update_status(data)

    def on_client_disconnected(self):
        self.adminLabel.setVisible(False)
        self.setStatus("disconnected")
        self.actionConnect.setIcon(get_icon("power-24px.svg"))
        self.actionConnect.setText("Connect to server...")
        self.actionExpert.setEnabled(False)
        self.actionViewOnly.setEnabled(False)
        self.actionEmergencyStop.setEnabled(False)
        self.setTitlebar(False)

    def on_client_showhelp(self, data):
        if not HelpWindow:
            return
        if self.helpWindow is None:
            self.helpWindow = HelpWindow(self, self.client)
        self.helpWindow.showHelp(data)
        self.helpWindow.activateWindow()

    def on_client_clientexec(self, data):
        # currently used for client-side plot using matplotlib; data is
        # (funcname, args, ...)
        plot_func_path = data[0]
        try:
            modname, funcname = plot_func_path.rsplit(".", 1)
            func = getattr(__import__(modname, None, None, [funcname]), funcname)
            func(*data[1:])
        except Exception:
            self.log.exception(
                "Error during clientexec:\n%s",
                "\n".join(traceback.format_tb(sys.exc_info()[2])),
            )

    def on_client_plugplay(self, data):
        windowkey = data[0:2]  # (mode, setupname)
        if windowkey in self.pnpWindows:
            self.pnpWindows[windowkey].activateWindow()
        else:
            window = PnPSetupQuestion(self, self.client, data)
            self.pnpWindows[windowkey] = window
            window.closed.connect(self.on_pnpWindow_closed)
            window.show()

    def on_pnpWindow_closed(self, window):
        self.pnpWindows.pop(window.data[0:2], None)

    def on_client_watchdog(self, data):
        if self.watchdogWindow is None:
            self.watchdogWindow = WatchdogDialog(self)
        self.watchdogWindow.addEvent(data)
        if data[0] != "resolved":
            self.watchdogWindow.show()

    def on_client_prompt(self, data):
        if self.promptWindow:
            self.promptWindow.close()

        # show non-modal dialog box that prompts the user to continue or abort
        prompt_text = data[0]
        dlg = self.promptWindow = QMessageBox(
            QMessageBox.Icon.Information,
            "Confirmation required",
            prompt_text,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            self,
        )
        dlg.setWindowModality(Qt.WindowModality.NonModal)

        # give the buttons better descriptions
        btn = dlg.button(QMessageBox.StandardButton.Cancel)
        btn.setText("Abort script")
        btn.clicked.connect(lambda: self.client.tell_action("stop", BREAK_NOW))
        btn = dlg.button(QMessageBox.StandardButton.Ok)
        btn.setText("Continue script")
        btn.clicked.connect(lambda: self.client.tell_action("continue"))
        btn.setFocus()

        dlg.show()

    def on_trayIcon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.activateWindow()

    def on_actionExpert_toggled(self, on):
        self.expertmode = on
        self.conndata.expertmode = on
        for panel in self.panels:
            panel.setExpertMode(on)
        for window in self.windows.values():
            for panel in window.panels:
                panel.setExpertMode(on)

    def on_actionViewOnly_triggered(self):
        self.conndata.viewonly = self.actionViewOnly.isChecked()

    def on_actionViewOnly_toggled(self, on):
        # also triggered when the action is checked by on_client_connected
        self.client.viewonly = on
        for panel in self.panels:
            panel.setViewOnly(on)
        for window in self.windows.values():
            for panel in window.panels:
                panel.setViewOnly(on)
        if self.client.isconnected:
            self.actionEmergencyStop.setEnabled(not self.client.viewonly)
        else:
            self.actionEmergencyStop.setEnabled(False)

    @pyqtSlot()
    def on_actionNicosHelp_triggered(self):
        if not HelpWindow:
            self.showError(
                "Cannot open help window: Qt web extension is not "
                "available on your system."
            )
            return
        if not self.client.isconnected:
            self.showError(
                "Cannot open online help: you are not connected " "to a daemon."
            )
            return
        self.client.eval('session.showHelp("index")')

    @pyqtSlot()
    def on_actionNicosDocu_triggered(self):
        if not QWebView:
            self.showError(
                "Cannot open documentation window: Qt web extension"
                " is not available on your system."
            )
            return
        from nicos.clients.gui.tools.website import WebsiteTool

        dlg = WebsiteTool(
            self,
            self.client,
            url="https://forge.frm2.tum.de/nicos/doc/nicos-master/documentation/",
        )
        dlg.setWindowModality(Qt.WindowModality.NonModal)
        dlg.show()

    @pyqtSlot()
    def on_actionDebugConsole_triggered(self):
        if self.debugConsole is None:
            self.debugConsole = DebugConsole(self)
        self.debugConsole.show()

    @pyqtSlot()
    def on_actionAbout_triggered(self):
        import nicos.authors

        if self.client.isconnected:
            dinfo = self.client.daemon_info.copy()
            dinfo["server_host"] = self.client.host
        else:
            dinfo = {}
        dlg = dialogFromUi(self, "dialogs/about.ui")
        dlg.clientVersion.setText(nicos_version)
        dlg.pyVersion.setText(
            "%s/%s/%s/%s/%s"
            % (
                sys.version.split()[0],
                QT_VERSION_STR,
                PYQT_VERSION_STR,
                gr.runtime_version(),
                gr.__version__,
            )
        )
        dlg.serverHost.setText(dinfo.get("server_host", "not connected"))
        dlg.nicosRoot.setText(dinfo.get("nicos_root", ""))
        dlg.serverVersion.setText(dinfo.get("daemon_version", ""))
        dlg.customPath.setText(dinfo.get("custom_path", ""))
        dlg.customVersion.setText(dinfo.get("custom_version", ""))
        dlg.contributors.setPlainText(nicos.authors.authors_list)
        dlg.adjustSize()
        dlg.exec()

    @pyqtSlot(bool)
    def on_actionConnect_triggered(self, on):
        # connection or disconnection request?
        if self.current_status != "disconnected":
            self.client.disconnect()
            return

        self.actionConnect.setChecked(False)  # gets set by connection event
        ret = ConnectionDialog.getConnectionData(
            self, self.connpresets, self.default_server, self.default_user
        )
        new_name, new_data, save, _ = ret

        if new_data is None:
            return
        if save:
            self.lastpreset = save
            self.connpresets[save] = new_data.copy()
        else:
            self.lastpreset = new_name
        self.setConnData(new_data)
        self.client.connect(self.conndata)

    @pyqtSlot()
    def on_actionPreferences_triggered(self):
        dlg = SettingsDialog(self)
        ret = dlg.exec()
        if ret == QDialog.DialogCode.Accepted:
            dlg.saveSettings()

    @pyqtSlot()
    def on_actionFont_triggered(self):
        font, ok = QFontDialog.getFont(self.user_font, self)
        if not ok:
            return
        for panel in self.panels:
            panel.setCustomStyle(font, self.user_color)
        self.user_font = font

    @pyqtSlot()
    def on_actionColor_triggered(self):
        color = QColorDialog.getColor(self.user_color, self)
        if not color.isValid():
            return
        for panel in self.panels:
            panel.setCustomStyle(self.user_font, color)
        self.user_color = color

    @pyqtSlot()
    def on_actionUser_triggered(self):
        w = self.toolBarRight.widgetForAction(self.actionUser)
        self.dropdown.popup(w.mapToGlobal(QPoint(0, w.height())))

    @pyqtSlot()
    def on_actionEmergencyStop_triggered(self):
        self.client.tell_action("emergency")
