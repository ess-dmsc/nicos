from nicos.clients.gui.widgets.lineedit import CommandLineEdit
from .utils import StyleSelector


class CommandLineEditStyleSheet(CommandLineEdit, StyleSelector):

    def setStatus(self, status):
        CommandLineEdit.setStatus(self, status)
        self.style_type = 1 if status != 'idle' else 0
        self.refresh_gui()
