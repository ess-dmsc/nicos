from nicos.clients.gui.widgets.lineedit import CommandLineEdit as \
    CommandLineEditBase
from .utils import State, StyleSelector, refresh_widget


class CommandLineEdit(CommandLineEditBase, StyleSelector):
    """
    This widget extends from CommandLineEdit in NICOS core and overrides all
    functions that are using widget palette dependent functions in the base
    class. Stylesheets is the preferred choice in NICOS ESS.
    """

    def setStatus(self, status):
        CommandLineEditBase.setStatus(self, status)
        self.state = State.BUSY if status != 'idle' \
            else State.DEFAULT
        refresh_widget(self)
