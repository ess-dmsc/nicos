from nicos.guisupport.qt import pyqtProperty


class StyleSelector:

    def __init__(self):
        self._style_type = "default"

    @pyqtProperty(str)
    def style_type(self):
        return self._style_type

    @style_type.setter
    def style_type(self, value):
        self._style_type = value


def refresh_widget(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
