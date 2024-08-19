"""NICOS GUI error and warning window."""

from logging import WARNING

from nicos.clients.gui.dialogs.traceback import TracebackDialog
from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import QDialogButtonBox
from nicos.guisupport.utils import setBackgroundColor
from nicos.utils import findResource


class ErrorPanel(Panel):
    """Provides an output view similar to the ConsolePanel.

    In comparison to the ConsolePanel it only displays messages with the
    WARNING and ERROR loglevel.
    """

    panelName = "Error window"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/errpanel.ui"))
        self.outView.setFullTimestamps(True)

        self.buttonBox.addButton("Clear", QDialogButtonBox.ButtonRole.ResetRole)

        if client.isconnected:
            self.on_client_connected()
        client.connected.connect(self.on_client_connected)
        client.message.connect(self.on_client_message)
        client.experiment.connect(self.on_client_experiment)

    def setCustomStyle(self, font, back):
        self.outView.setFont(font)
        setBackgroundColor(self.outView, back)

    def on_client_connected(self):
        messages = self.client.ask("getmessages", "10000", default=[])
        self.outView.clear()
        self.outView.addMessages([msg for msg in messages if msg[2] >= WARNING])
        self.outView.scrollToBottom()

    def on_client_message(self, message):
        if message[2] >= WARNING:  # show if level is warning or higher
            self.outView.addMessage(message)

    def on_client_experiment(self, data):
        (_, proptype) = data
        if proptype == "user":
            # only clear output when switching TO a user experiment
            self.outView.clear()

    def on_outView_anchorClicked(self, url):
        """Called when the user clicks a link in the out view."""
        if url.scheme() == "trace":
            TracebackDialog(self, self.outView, url.path()).show()

    def on_buttonBox_clicked(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QDialogButtonBox.ButtonRole.ResetRole:
            self.outView.clear()
        elif role == QDialogButtonBox.ButtonRole.RejectRole:
            self.closeWindow()
