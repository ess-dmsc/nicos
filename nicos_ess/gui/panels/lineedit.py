import total as total

from nicos.clients.gui.widgets.lineedit import CommandLineEdit
from nicos.guisupport.qt import pyqtProperty


class CommandLineEditStyleSheet(CommandLineEdit):

    def __init__(self, parent, history=None):
        super().__init__(parent, history)
        self._change_style = False

    def setStatus(self, status):
        CommandLineEdit.setStatus(self, status)
        self._change_style = True if status != 'idle' else False
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    @pyqtProperty(bool)
    def change_style(self):
        return self._change_style

    @change_style.setter
    def change_style(self, current_status):
        self._change_style = current_status
