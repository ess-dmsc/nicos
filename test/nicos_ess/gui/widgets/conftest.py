"""Standalone pyqtgraph widget fixtures."""

import pytest


@pytest.fixture
def show_widget(qtbot):
    from nicos.guisupport.qt import QApplication, QEvent

    def _show(widget, width=400, height=300):
        top = widget.window()
        qtbot.addWidget(top)
        top.resize(width, height)
        widget.resize(width, height)
        with qtbot.waitExposed(top):
            top.show()
        QApplication.processEvents()
        return widget

    yield _show

    # qtbot has closed the widgets and called deleteLater on them. Until the
    # delete runs, pyqtgraph timers of the widgets can fire into the next test.
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture
def view(qtbot):
    """An empty FrameView on a shown canvas of 600 by 400 pixels."""
    from test.nicos_ess.gui.widgets.frames import make_view

    return make_view(qtbot)
