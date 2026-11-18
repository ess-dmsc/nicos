"""Frames, plots and fake pyqtgraph events that several plot tests share."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pyqtgraph as pg

from nicos.guisupport.qt import Qt
from nicos_ess.gui.widgets.pyqtgraph.frame_plot import FrameView
from nicos_ess.utilities.live_frame import Coord, Frame


class FakeClick:
    """Fake pyqtgraph left click at a scene position."""

    def __init__(self, scene_pos, double=False):
        self.at, self.is_double, self.accepted = scene_pos, double, False

    def button(self):
        return Qt.MouseButton.LeftButton

    def double(self):
        return self.is_double

    def scenePos(self):
        return self.at

    screenPos = scenePos

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.accepted = False


class FakeWheel:
    """Fake pyqtgraph wheel event that turns one notch up at a scene position."""

    def __init__(self, scene_pos):
        self.at, self.accepted = scene_pos, False

    def scenePos(self):
        return self.at

    def delta(self):
        return 120

    def modifiers(self):
        return Qt.KeyboardModifier.NoModifier

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.accepted = False


def histogram(**changes):
    counts = np.array([1.0, 4.0, 9.0])
    frame = Frame(
        counts,
        ("tof",),
        unit="counts",
        counts=True,
        title="Monitor histogram",
        coords={"tof": Coord(("tof",), np.array([0.0, 1e3, 2e3, 3e3]), "us")},
        errors=np.sqrt(counts),
        name="monitor_1",
    )
    return replace(frame, **changes)


def cube():
    return Frame(
        np.arange(4 * 5 * 6, dtype=np.float64).reshape(4, 5, 6),
        ("wavelength", "y", "x"),
        unit="counts",
        counts=True,
        title="Detector counts",
        coords={"wavelength": Coord(("wavelength",), np.linspace(1, 5, 5), "angstrom")},
        name="detector_image",
    )


def image(value, shape=(2, 3), dims=("y", "x"), **options):
    options = {"unit": "counts", "counts": True, **options}
    return Frame(np.full(shape, value, dtype=float), dims, **options)


def curve(dim, edges, unit, values=None):
    values = np.arange(len(edges) - 1.0) if values is None else values
    return Frame(
        values,
        (dim,),
        unit="counts",
        counts=True,
        coords={dim: Coord((dim,), edges, unit)},
    )


def millimetres(x, y=(0.0, 10.0, 20.0, 30.0)):
    """Return the coords of an image whose pixel edges are *x* and *y* in mm."""
    edges = {"x": x, "y": y}
    return {d: Coord((d,), np.array(e, dtype=float), "mm") for d, e in edges.items()}


def make_view(qtbot, **options):
    canvas = pg.GraphicsLayoutWidget()
    qtbot.addWidget(canvas)
    frame_view = FrameView("out", **options)
    canvas.ci.addItem(frame_view.item)
    canvas.resize(600, 400)
    canvas.show()
    frame_view.canvas = canvas  # qtbot does not keep a reference to the canvas
    return frame_view


def wait_exposed(qtbot, widget):
    """Wait until the window of a shown *widget* is on the screen."""
    qtbot.waitUntil(lambda: widget.windowHandle().isExposed())
