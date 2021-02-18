from enum import Enum
from nicos.guisupport.qt import pyqtProperty


class State(Enum):
    DEFAULT, BUSY = range(2)


class StyleSelector:
    """
    A class that encapsulates the state used for stylesheet selection
    in the relevant qss files.
    """

    def __init__(self):
        self.state = State.DEFAULT

    @pyqtProperty(str)
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = str(value).split(".")[-1]


def refresh_widget(widget):
    """
    Function that correctly updates the widget with a new stylesheet.
    """
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
