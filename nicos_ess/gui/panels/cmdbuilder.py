"""NICOS GUI command input."""

from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi, modePrompt
from nicos.guisupport.qt import QApplication, QKeyEvent, Qt, pyqtSlot
from nicos.guisupport.utils import setBackgroundColor
from nicos.utils import findResource

from nicos_ess.gui.utils import get_icon


class CommandPanel(Panel):
    """Provides a panel where the user can run Python commands."""

    panelName = "Command"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/cmdbuilder.ui"))

        self.parent_window = parent
        self.options = options
        self.mapping = {}
        self.expertmode = self.mainwindow.expertmode

        self.commandInput.history = self.cmdhistory
        self.commandInput.completion_callback = self.completeInput
        self.console = None

        client.initstatus.connect(self.on_client_initstatus)
        client.mode.connect(self.on_client_mode)

        self.set_icons()
        if client.isconnected:
            self.on_client_connected()
        else:
            self.on_client_disconnected()
        client.connected.connect(self.on_client_connected)
        client.disconnected.connect(self.on_client_disconnected)

    def postInit(self):
        self.console = self.parent_window.getPanel("Console")
        if self.console:
            self.console.outView.anchorClicked.connect(
                self.on_consoleView_anchorClicked
            )

    def on_client_connected(self):
        self.setViewOnly(self.client.viewonly)

    def on_client_disconnected(self):
        self.setViewOnly(True)

    def set_icons(self):
        self.runBtn.setIcon(get_icon("play_arrow-24px.svg"))

    def setViewOnly(self, viewonly):
        self.inputFrame.setEnabled(not viewonly)

    def loadSettings(self, settings):
        self.cmdhistory = settings.value("cmdhistory") or []

    def saveSettings(self, settings):
        # only save 100 entries of the history
        cmdhistory = self.commandInput.history[-100:]
        settings.setValue("cmdhistory", cmdhistory)

    def updateStatus(self, status, exception=False):
        self.commandInput.setStatus(status)

    def setCustomStyle(self, font, back):
        self.commandInput.idle_color = back
        self.commandInput.setFont(font)
        setBackgroundColor(self.commandInput, back)

    def getMenus(self):
        return []

    def setExpertMode(self, expert):
        self.expertmode = expert

    def completeInput(self, fullstring, lastword):
        try:
            return self.client.ask("complete", fullstring, lastword, default=[])
        except Exception:
            return []

    def on_client_initstatus(self, state):
        self.on_client_mode(state["mode"])

    def on_client_mode(self, mode):
        self.label.setText(modePrompt(mode))

    def on_consoleView_anchorClicked(self, url):
        """Called when the user clicks a link in the out view."""
        scheme = url.scheme()
        if scheme == "exec":
            self.commandInput.setText(url.path())
            self.commandInput.setFocus()

    @pyqtSlot()
    def on_runBtn_clicked(self):
        # Make sure we add the command to the history.
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Enter, Qt.KeyboardModifier.NoModifier
        )
        QApplication.postEvent(self.commandInput, event)

    def on_commandInput_execRequested(self, script, action):
        if action == "queue":
            self.client.run(script)
        else:
            self.client.tell("exec", script)
        self.commandInput.selectAll()
        self.commandInput.setFocus()
        self.commandInput.clear()
