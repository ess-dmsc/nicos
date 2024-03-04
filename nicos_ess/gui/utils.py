from enum import Enum
from os import path

from nicos import config
from nicos.guisupport.qt import QIcon, pyqtProperty

root_path = config.nicos_root
icons_path = path.join(root_path, 'resources', 'material', 'icons')


def get_icon(icon_name):
    return QIcon(path.join(icons_path, icon_name))


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
    def state(self):  # pylint: disable=method-hidden
        return self._state

    @state.setter
    def state(self, value):
        self._state = str(value).rsplit('.', maxsplit=1)[-1]


def refresh_widget(widget):
    """
    Function that correctly updates the widget with a new stylesheet.
    """
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()