# ruff: noqa: E402
"""The chopper widget as rendered: openings where the real discs have them.

Pixel probes on an offscreen render, angles in Qt screen degrees (anticlockwise
from 3 o'clock). Expected positions come from observed discs, see
test_chopper_math.py.
"""

import os
from math import cos, radians, sin

import pytest

qt = pytest.importorskip(
    "nicos.guisupport.qt", reason="PyQt is required for standalone ChopperWidget tests"
)
QApplication = qt.QApplication
QPointF = qt.QPointF
QPixmap = qt.QPixmap
Qt = qt.Qt
from nicos_ess.devices.chopper_math import is_chopper_moving
from nicos_ess.gui.widgets.chopper_widget import ChopperWidget, spin_arc
from test.nicos_ess.test_devices.test_chopper_math import (
    DOWN,
    LEFT,
    OVERLAP,
    PSC2,
    TPSC101,
    TPSC102,
    UP,
    WFMC1,
    WFMC1_FAT_PARK,
    disc,
)


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _widget(*choppers, guide_line=False):
    widget = ChopperWidget()
    widget._show_guide_line = guide_line
    widget.update_chopper_data(
        [dict(c, chopper=f"c{i}") for i, c in enumerate(choppers)]
    )
    return widget


def _show(widget, speed, angle, index=0):
    """Parked: Pos_R = angle. Spinning: TotDly (ns) that turns the disc by angle."""
    name = f"c{index}"
    widget.set_value(name, "speed", speed)
    if is_chopper_moving(speed):
        widget.set_value(name, "total_delay", angle / 360.0 / abs(speed) * 1e9)
    else:
        widget.set_value(name, "park_angle", angle)


def _rotation(widget):
    return widget.rotation(widget.chopper_data[0])


def _render(widget, qapp):
    widget.resize(420, 420)
    qapp.processEvents()
    pixmap = QPixmap(widget.size())
    pixmap.fill(Qt.GlobalColor.white)
    widget.render(pixmap)
    positions, radius = widget.layout_discs()
    return pixmap.toImage(), positions[0], radius


def _count(image, center, radius, angle_deg, predicate, spread=1):
    theta = radians(angle_deg)
    x = int(round(center.x() + radius * cos(theta)))
    y = int(round(center.y() - radius * sin(theta)))
    hits = 0
    for dx in range(-spread, spread + 1):
        for dy in range(-spread, spread + 1):
            sx = min(max(x + dx, 0), image.width() - 1)
            sy = min(max(y + dy, 0), image.height() - 1)
            hits += predicate(image.pixelColor(sx, sy))
    return hits


def _dark(color):
    return color.red() < 50 and color.green() < 50 and color.blue() < 50


def _blade_is_dark(widget, qapp, angle_deg):
    """Probe the coated blade ring (black where there is absorber)."""
    image, center, radius = _render(widget, qapp)
    slit = radius * 0.3
    ring = ((radius - slit + radius * 0.05) + radius * 0.95) / 2.0
    return _count(image, center, ring, angle_deg, _dark) >= 5


def _assert_open_at(widget, qapp, angle_deg, half_width=1.5, outside=12.0):
    assert not _blade_is_dark(widget, qapp, angle_deg)
    assert not _blade_is_dark(widget, qapp, angle_deg + half_width)
    assert not _blade_is_dark(widget, qapp, angle_deg - half_width)
    assert _blade_is_dark(widget, qapp, angle_deg + outside)
    assert _blade_is_dark(widget, qapp, angle_deg - outside)


@pytest.mark.parametrize(
    ("chopper", "reading", "where"),
    [
        (TPSC101, 333.0, DOWN),
        (TPSC101, 243.0, LEFT),
        (TPSC102, 329.3, DOWN),
        (TPSC102, 59.3, LEFT),
    ],
)
def test_heimdal_parked_renders_as_seen_in_the_lab(qapp, chopper, reading, where):
    widget = _widget(chopper)
    _show(widget, 0.0, reading)
    _assert_open_at(widget, qapp, where)


@pytest.mark.parametrize(
    ("chopper", "speed", "phase"),
    [
        (TPSC101, 70.0, 357.0 - 5.3),
        (TPSC101, -70.0, 14.9 - 6.6),
        (TPSC102, 70.0, 18.85 - 6.25),
        (TPSC102, -70.0, 352.9 - 5.5),
    ],
)
def test_heimdal_spinning_renders_as_seen_in_the_lab(qapp, chopper, speed, phase):
    widget = _widget(chopper)
    _show(widget, speed, phase)
    _assert_open_at(widget, qapp, DOWN)


@pytest.mark.parametrize("index", [1, 3, 5])
def test_odin_wfmc1_renders_the_parked_cut_out_with_its_width(qapp, index):
    """Asymmetric disc: a mirrored drawing would put the wrong cut-out here."""
    widget = _widget(WFMC1)
    _show(widget, 0.0, WFMC1_FAT_PARK[index])
    start, end = WFMC1["slit_edges"][index]
    half = (end - start) / 2.0
    _assert_open_at(widget, qapp, DOWN, half_width=half - 1.5, outside=half + 2.5)


def test_dream_psc2_renders_open_above_the_axle(qapp):
    widget = _widget(PSC2)
    _show(widget, 0.0, 49.3)
    _assert_open_at(widget, qapp, UP, half_width=1.0, outside=6.0)


def test_dream_overlap_is_drawn_parked_open_without_a_pos_r(qapp):
    widget = _widget(OVERLAP)
    widget.set_value("c0", "speed", 0.0)
    _assert_open_at(widget, qapp, DOWN, half_width=10.0, outside=20.0)
    _show(widget, 14.0, 0.0)
    _assert_open_at(widget, qapp, DOWN, half_width=10.0, outside=20.0)


def test_motion_state_uses_the_absolute_speed(qapp):
    widget = _widget(TPSC101)
    _show(widget, -1.9, 10.0)
    parked = _rotation(widget)
    _show(widget, -2.1, 10.0)
    assert _rotation(widget) != parked


def test_nothing_is_drawn_before_an_angle_arrives(qapp):
    widget = _widget(TPSC101)
    widget.set_value("c0", "speed", 0.0)
    assert _rotation(widget) is None


def test_invalid_geometry_is_rejected(qapp):
    with pytest.raises(ValueError, match="beam_position"):
        _widget(dict(TPSC101, beam_position=None))


def test_discs_are_drawn_in_beam_order(qapp):
    widget = ChopperWidget()
    widget.update_chopper_data(
        [
            dict(TPSC101, chopper="no_distance_1"),
            dict(TPSC101, chopper="far", distance=13.05),
            dict(TPSC101, chopper="no_distance_2"),
            dict(TPSC101, chopper="near", distance=6.15),
        ]
    )
    assert [c["chopper"] for c in widget.chopper_data] == [
        "near",
        "far",
        "no_distance_1",
        "no_distance_2",
    ]


def test_full_circle_opening_stays_open(qapp):
    widget = _widget(disc([[0.0, 360.0]], 0.0, 1, 0.0))
    _show(widget, 0.0, 30.0)
    assert not _blade_is_dark(widget, qapp, DOWN)
    assert not _blade_is_dark(widget, qapp, DOWN + 90.0)


@pytest.mark.parametrize(("guide", "name_above"), [("DOWN", True), ("UP", False)])
def test_name_outside_the_disc_and_status_inside(qapp, guide, name_above):
    chopper = dict(TPSC101, guide_position=guide)
    widget = _widget(chopper)
    rects = widget._label_rects(
        widget.chopper_data[0], QPointF(100.0, 100.0), 50.0, 3, 10.0
    )
    name, value, status = (r.normalized() for r in rects)
    if name_above:
        assert name.bottom() < 100.0 - 50.0
    else:
        assert name.top() > 100.0 + 50.0
    for rect in (value, status):
        assert abs(rect.center().x() - 100.0) < 50.0
        assert abs(rect.center().y() - 100.0) < 50.0


@pytest.mark.parametrize(("speed", "clockwise"), [(14.0, True), (-14.0, False)])
def test_spin_indicator_turns_with_the_disc(qapp, speed, clockwise):
    widget = _widget(TPSC101)
    _show(widget, speed, 0.0)
    start, sweep = spin_arc(DOWN, clockwise)
    # clockwise on screen: the arrow runs to smaller angles, across the beam
    assert sweep == pytest.approx(-72.0 if clockwise else 72.0)
    assert start + sweep / 2 == pytest.approx(DOWN)
    image, center, radius = _render(widget, qapp)

    def arrow(color):  # translucent black over the green "rotating" fill
        return color.red() < 60 and color.green() < 60 and color.blue() < 60

    assert _count(image, center, radius * 1.1 * 0.5, DOWN, arrow, spread=3) >= 3
