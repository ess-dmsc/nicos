import tempfile
from pathlib import Path

import numpy as np
import pytest

from nicos_ess.gui.widgets.pyqtgraph import export
from nicos_ess.gui.widgets.pyqtgraph.export import (
    IMAGE_FILTERS,
    export_plot,
    save_plot_dialog,
    save_plot_quietly,
)
from nicos_ess.gui.widgets.pyqtgraph.frame_plot import FrameCanvas, FrameView
from nicos_ess.utilities.live_frame import curve_frame

X = np.linspace(-5.0, 5.0, 201)


@pytest.fixture
def canvas(show_widget):
    view = FrameView("curve")
    return show_widget(FrameCanvas(view))


def show_curve(canvas):
    canvas.view.show_frame(curve_frame("x", "", X, X, errors=np.ones_like(X)))


@pytest.mark.parametrize("suffix", [".png", ".svg", ".pdf"])
def test_export_plot_writes_the_curve(canvas, tmp_path, suffix):
    # An export of the empty plot is already larger than a few kilobytes, so
    # the plot with the curve has to be larger than the empty plot.
    export_plot(canvas, tmp_path / f"empty{suffix}")
    show_curve(canvas)

    export_plot(canvas, tmp_path / f"plot{suffix}")

    empty_size = (tmp_path / f"empty{suffix}").stat().st_size
    assert (tmp_path / f"plot{suffix}").stat().st_size > empty_size + 1000


def test_export_plot_refuses_an_unknown_format(canvas, tmp_path):
    with pytest.raises(ValueError, match="unsupported plot format: .jpg"):
        export_plot(canvas, tmp_path / "plot.jpg")
    assert not (tmp_path / "plot.jpg").exists()


def test_save_plot_quietly_writes_svg_and_png(canvas, tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    show_curve(canvas)

    saved = save_plot_quietly(canvas)

    assert [suffix for _path, suffix in saved] == [".svg", ".png"]
    for path, suffix in saved:
        assert Path(path).parent == tmp_path
        assert Path(path).suffix == suffix
        assert Path(path).stat().st_size > 1000


def test_save_plot_dialog_adds_the_suffix_of_the_chosen_filter(
    canvas, tmp_path, monkeypatch
):
    monkeypatch.setattr(export, "_saved", "plot")
    monkeypatch.setattr(
        export.QFileDialog,
        "getSaveFileName",
        lambda *args: (str(tmp_path / "plot"), IMAGE_FILTERS[".pdf"]),
    )
    show_curve(canvas)

    saved = save_plot_dialog(canvas)

    assert saved == str(tmp_path / "plot.pdf")
    assert (tmp_path / "plot.pdf").stat().st_size > 1000
