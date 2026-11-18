"""Tests of the ESS GUI style sheet nicos_ess/gui/guiconfig.qss on plain widgets."""

from pathlib import Path

import pytest

import nicos_ess
from nicos.guisupport.qt import (
    QMenu,
    QSplitter,
    QWidget,
)


@pytest.fixture(autouse=True)
def ess_style(qapp):
    previous = qapp.styleSheet()
    qss = Path(nicos_ess.__file__).parent / "gui" / "guiconfig.qss"
    qapp.setStyleSheet(qss.read_text(encoding="utf-8"))
    yield
    qapp.setStyleSheet(previous)


def shown(qtbot, widget, height=None):
    widget.resize(200, height or widget.sizeHint().height())
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget.grab().toImage()


def section_text_pixels(qtbot):
    """Count the dark pixels that the title adds to a menu section row."""

    def dark_pixels(title):
        menu = QMenu()
        menu.addSection(title)
        menu.addAction("Entry")
        qtbot.addWidget(menu)
        # Showing a popup menu makes the offscreen platform warn, so the test
        # polishes the hidden menu with the current style sheet instead.
        menu.ensurePolished()
        image = menu.grab().toImage()
        row = menu.actionGeometry(menu.actions()[0])
        return sum(
            image.pixelColor(x, y).lightness() < 128
            for x in range(row.left(), row.right())
            for y in range(row.top(), row.bottom())
        )

    return dark_pixels("Colormaps") - dark_pixels("")


def test_menu_section_titles_keep_their_text(qtbot, qapp):
    """A QMenu background, border or ::separator rule makes Qt draw the section
    titles as bare lines."""
    with_ess_style = section_text_pixels(qtbot)
    ess_style = qapp.styleSheet()
    qapp.setStyleSheet("")
    without_style = section_text_pixels(qtbot)
    qapp.setStyleSheet(ess_style)
    assert without_style > 0, "Qt draws no menu text here, maybe no font is found"
    # The palette rules may change the text colour a little, so the ESS style
    # only has to keep most of the dark text pixels.
    assert with_ess_style > without_style // 2


def test_splitter_handles_show_a_line_along_their_length(qtbot):
    split = QSplitter()
    split.setHandleWidth(5)
    split.addWidget(QWidget())
    split.addWidget(QWidget())
    # The splitter paints its white background under the handle, so the grab of
    # the whole splitter has no transparent pixels around the line.
    image = shown(qtbot, split, height=60)
    handle = split.handle(1).geometry()
    # Check near both ends because a grip in the middle is not enough.
    for y in (handle.top() + 2, handle.bottom() - 2):
        colors = [
            image.pixelColor(x, y) for x in range(handle.left(), handle.right() + 1)
        ]
        assert all(color.alpha() == 255 for color in colors)
        assert min(color.lightness() for color in colors) < 230
