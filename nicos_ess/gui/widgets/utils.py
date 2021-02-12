from nicos.guisupport.qt import pyqtProperty


class StyleSelector:

    def __init__(self):
        self._style_type = 0

    @pyqtProperty(int)
    def style_type(self):
        return self._style_type

    @style_type.setter
    def style_type(self, value):
        self._style_type = value


def refresh_widget(widget):
    try:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
    except AttributeError as e:
        print(e)


