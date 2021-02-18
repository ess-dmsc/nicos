from nicos.clients.gui.widgets.lineedit import CommandLineEdit as \
    CommandLineEditBase
from .utils import State, StyleSelector, refresh_widget


class CommandLineEdit(CommandLineEditBase, StyleSelector):
    """
    Why do we have this class? Because Palettes can't be used
    """
    def setStatus(self, status):
        CommandLineEditBase.setStatus(self, status)
        self.state = State.BUSY if status != 'idle' \
            else State.DEFAULT
        refresh_widget(self)
