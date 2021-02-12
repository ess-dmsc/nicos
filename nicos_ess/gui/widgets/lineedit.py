from nicos.clients.gui.widgets.lineedit import CommandLineEdit
from .utils import StyleSelector, refresh_widget


class CommandLineEditStyleSheet(CommandLineEdit, StyleSelector):

    def setStatus(self, status):
        CommandLineEdit.setStatus(self, status)
        self.style_type = "busy" if status != 'idle' else "default"
        refresh_widget(self)
