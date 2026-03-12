import os
from math import cos, radians, sin

import pytest

qt = pytest.importorskip(
    "nicos.guisupport.qt", reason="PyQt is required for standalone ChopperWidget tests"
)
QApplication = qt.QApplication
QPainter = qt.QPainter
QPointF = qt.QPointF
QPixmap = qt.QPixmap
from nicos_ess.gui.widgets.chopper_math import (
    build_rotation_model,
    apply_motor_side_transform,
    direction_to_sign,
    opening_center_deg,
    runtime_phase_sign,
    wrap180,
    wrap360,
)
from nicos_ess.gui.widgets.chopper_widget import ChopperWidget


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _canonical(name, **overrides):
    data = {
        "chopper": name,
        "slit_edges": [[0.0, 90.0]],
        "motor_position": "downstream",
        "disk_rotation_direction": "CW",
        "parked_opening_index": 0,
        "tdc_resolver_position": 60.0,
        "park_open_angle": 30.0,
        "phase_tdc_center_window_delay": 30.0,
    }
    data.update(overrides)
    return data


def _delta(after, before):
    return wrap180(after - before)


def _ymir_psc(name, **overrides):
    """Canonical PSC inputs copied from `ymir/setups/choppers_dream.py`."""
    return _canonical(name, **overrides)


def _resolver_angles_for_all_openings(chopper):
    """Compute parked resolver angle for each opening from one known reference."""
    centers = [opening_center_deg(edges) for edges in chopper["slit_edges"]]
    ref_idx = int(chopper["parked_opening_index"])
    ref_center = centers[ref_idx]
    ref_resolver = float(chopper["park_open_angle"])

    base_direction = apply_motor_side_transform(
        chopper["disk_rotation_direction"], chopper["motor_position"]
    )
    resolver_sign = direction_to_sign(base_direction)

    return [
        wrap360(ref_resolver + resolver_sign * (ref_center - center))
        for center in centers
    ]


def _phase_angles_for_all_openings(chopper, speed_hz):
    """Compute spinning phase setpoint per opening from configured phase reference."""
    centers = [opening_center_deg(edges) for edges in chopper["slit_edges"]]
    ref_idx = int(chopper["parked_opening_index"])
    ref_center = centers[ref_idx]
    ref_phase = float(chopper["phase_tdc_center_window_delay"])

    model = build_rotation_model(chopper)
    spin_sign = runtime_phase_sign(
        speed_hz, model.base_spin_direction, model.phase_reference_sign
    )

    return [
        wrap360(ref_phase + spin_sign * (center - ref_center))
        for center in centers
    ]


def _coating_covers_guide(widget, chopper, rotation_angle):
    """Return True when the coating path covers the beam-guide direction."""
    radius = 100.0
    slit_height = radius * 0.3
    reduced_radius = radius - slit_height
    inner_coating = reduced_radius + radius * 0.05
    outer_coating = radius * 0.95
    guide_probe_radius = (inner_coating + outer_coating) / 2.0

    center = QPointF(0.0, 0.0)
    coating_path = widget._annulus_with_opening_holes(
        center,
        inner_coating,
        outer_coating,
        chopper["slit_edges"],
        rotation_angle,
    )

    guide_theta = radians(widget._guide_angle_deg)
    probe_point = QPointF(
        center.x() + guide_probe_radius * cos(guide_theta),
        center.y() - guide_probe_radius * sin(guide_theta),
    )
    return coating_path.contains(probe_point)


def _opening_intervals_qt(chopper, rotation_angle):
    """Opening intervals in widget Qt-angle coordinates for one chopper."""
    intervals = []
    for start, end in chopper["slit_edges"]:
        intervals.append((wrap360(-float(end) + rotation_angle), wrap360(-float(start) + rotation_angle)))
    return intervals


def _interval_contains(angle, interval):
    angle = wrap360(angle)
    start, end = interval
    if end < start:
        return angle >= start or angle <= end
    return start <= angle <= end


def _dream_psc_cases():
    # Values taken from `nicos_ess/ymir/setups/choppers_dream.py`.
    psc1 = _ymir_psc(
        "pulse_shaping_chopper_1",
        slit_edges=[
            [0.0, 2.46],
            [71.72, 74.74],
            [85.995, 89.265],
            [114.795, 118.065],
            [171.52, 176.54],
            [272.865, 276.795],
            [287.265, 291.195],
            [302.4, 304.86],
        ],
        parked_opening_index=4,
        motor_position="downstream",
        disk_rotation_direction="CW",
        tdc_resolver_position=342.0,
        park_open_angle=321.5,
        phase_tdc_center_window_delay=20.5,
    )
    psc2 = _ymir_psc(
        "pulse_shaping_chopper_2",
        slit_edges=[
            [0.0, 2.46],
            [28.23, 31.83],
            [57.03, 60.63],
            [143.615, 146.845],
            [157.995, 161.265],
            [215.345, 219.115],
            [258.46, 262.4],
            [316.72, 319.34],
        ],
        parked_opening_index=6,
        motor_position="downstream",
        disk_rotation_direction="CW",
        tdc_resolver_position=342.0,
        park_open_angle=49.3,
        phase_tdc_center_window_delay=292.7,
    )
    return [psc1, psc2]


def _nmx_wls2_pair():
    # Values taken from `nicos_ess/ymir/setups/choppers_nmx.py`.
    wls2a = _canonical(
        "wls2a",
        slit_edges=[[0.0, 170.0]],
        motor_position="upstream",
        disk_rotation_direction="CW",
        parked_opening_index=0,
        tdc_resolver_position=341.7,
        park_open_angle=73.0,
        phase_tdc_center_window_delay=91.3,
    )
    wls2b = _canonical(
        "wls2b",
        slit_edges=[[0.0, 170.0]],
        motor_position="downstream",
        disk_rotation_direction="CW",
        parked_opening_index=0,
        tdc_resolver_position=342.5,
        park_open_angle=165.0,
        phase_tdc_center_window_delay=177.5,
    )
    return wls2a, wls2b


def test_widget_returns_none_for_missing_canonical(qapp):
    widget = ChopperWidget()
    widget.update_chopper_data([{"chopper": "c1", "slit_edges": [[0.0, 90.0]]}])
    widget.set_chopper_speed("c1", 10.0)
    widget.set_chopper_angle("c1", 5.0)
    assert widget.get_rotation_angle_for_chopper("c1") is None


def test_widget_detailed_view_toggle_state(qapp):
    widget = ChopperWidget()
    assert not widget.is_detailed_view_enabled()
    widget.set_detailed_view(True)
    assert widget.is_detailed_view_enabled()
    widget.set_detailed_view(False)
    assert not widget.is_detailed_view_enabled()


def test_widget_tdc_marker_angle_available_for_canonical_inputs(qapp):
    widget = ChopperWidget(guide_pos="DOWN")
    canonical = _canonical("c1")
    widget.update_chopper_data([canonical])
    angle = widget.get_tdc_marker_angle_for_chopper("c1")
    assert angle is not None
    assert 0.0 <= angle < 360.0


def test_widget_tdc_marker_angle_missing_for_noncanonical_inputs(qapp):
    widget = ChopperWidget()
    widget.update_chopper_data([{"chopper": "c1", "slit_edges": [[0.0, 90.0]]}])
    assert widget.get_tdc_marker_angle_for_chopper("c1") is None


def test_widget_spin_direction_sign_tracks_runtime_phase_sign(qapp):
    down = _canonical("downstream", motor_position="downstream")
    up = _canonical("upstream", motor_position="upstream")
    widget = ChopperWidget()
    widget.update_chopper_data([down, up])

    widget.set_chopper_speed("downstream", 10.0)
    widget.set_chopper_speed("upstream", 10.0)
    assert widget.get_spin_direction_sign_for_chopper("downstream") == -1
    assert widget.get_spin_direction_sign_for_chopper("upstream") == -1

    widget.set_chopper_speed("downstream", -10.0)
    widget.set_chopper_speed("upstream", -10.0)
    assert widget.get_spin_direction_sign_for_chopper("downstream") == 1
    assert widget.get_spin_direction_sign_for_chopper("upstream") == 1


def test_widget_spin_indicator_arc_moves_with_guide_position(qapp):
    widget = ChopperWidget(guide_pos="DOWN")
    assert widget._spin_indicator_arc_angles(1) == pytest.approx((306.0, 234.0))
    assert widget._spin_indicator_arc_angles(-1) == pytest.approx((234.0, 306.0))

    widget.set_guide_position("RIGHT")
    assert widget._spin_indicator_arc_angles(1) == pytest.approx((36.0, 324.0))
    assert widget._spin_indicator_arc_angles(-1) == pytest.approx((324.0, 36.0))


def test_widget_spin_indicator_drawing_executes(qapp):
    widget = ChopperWidget(guide_pos="DOWN")
    pixmap = QPixmap(320, 320)
    painter = QPainter(pixmap)
    try:
        widget._draw_spin_direction_indicator(painter, QPointF(160.0, 160.0), 90.0, 1)
        widget._draw_spin_direction_indicator(painter, QPointF(160.0, 160.0), 90.0, -1)
    finally:
        painter.end()


@pytest.mark.parametrize(
    "chopper",
    [
        _canonical("downstream", motor_position="downstream"),
        _canonical("upstream", motor_position="upstream"),
    ],
    ids=lambda c: c["chopper"],
)
def test_widget_phase_perturbation_moves_opposite_runtime_phase_direction(qapp, chopper):
    widget = ChopperWidget()
    widget.update_chopper_data([chopper])
    name = chopper["chopper"]
    speed_hz = 14.0
    eps = 0.2
    phase0 = float(chopper["phase_tdc_center_window_delay"])

    widget.set_chopper_speed(name, speed_hz)
    widget.set_chopper_angle(name, phase0)
    rot0 = widget.get_rotation_angle_for_chopper(name, include_guide=False)
    widget.set_chopper_angle(name, phase0 + eps)
    rot1 = widget.get_rotation_angle_for_chopper(name, include_guide=False)
    assert rot0 is not None
    assert rot1 is not None

    model = build_rotation_model(chopper)
    expected_delta = -runtime_phase_sign(
        speed_hz, model.base_spin_direction, model.phase_reference_sign
    ) * eps
    assert wrap180(rot1 - rot0) == pytest.approx(expected_delta)


@pytest.mark.parametrize(
    "chopper",
    [
        _canonical("downstream", motor_position="downstream"),
        _canonical("upstream", motor_position="upstream"),
    ],
    ids=lambda c: c["chopper"],
)
def test_widget_phase_perturbation_moves_opposite_displayed_spin_arrow(qapp, chopper):
    widget = ChopperWidget()
    widget.update_chopper_data([chopper])
    name = chopper["chopper"]
    speed_hz = 14.0
    eps = 0.2
    phase0 = float(chopper["phase_tdc_center_window_delay"])

    widget.set_chopper_speed(name, speed_hz)
    arrow_sign = widget.get_spin_direction_sign_for_chopper(name)
    assert arrow_sign is not None

    widget.set_chopper_angle(name, phase0)
    rot0 = widget.get_rotation_angle_for_chopper(name, include_guide=True)
    widget.set_chopper_angle(name, phase0 + eps)
    rot1 = widget.get_rotation_angle_for_chopper(name, include_guide=True)
    assert rot0 is not None
    assert rot1 is not None

    # arrow_sign uses CW-positive convention; include_guide angle increases in
    # Qt's CCW-positive sense. Opposite motion therefore maps to +arrow_sign.
    assert wrap180(rot1 - rot0) == pytest.approx(arrow_sign * eps)


@pytest.mark.parametrize(
    "chopper",
    [
        _canonical("downstream", motor_position="downstream"),
        _canonical("upstream", motor_position="upstream"),
    ],
    ids=lambda c: c["chopper"],
)
def test_widget_resolver_perturbation_moves_with_base_spin_direction(qapp, chopper):
    widget = ChopperWidget()
    widget.update_chopper_data([chopper])
    name = chopper["chopper"]
    eps = 0.2
    resolver0 = float(chopper["park_open_angle"])

    widget.set_chopper_speed(name, 0.0)
    widget.set_chopper_angle(name, resolver0)
    rot0 = widget.get_rotation_angle_for_chopper(name, include_guide=False)
    widget.set_chopper_angle(name, resolver0 + eps)
    rot1 = widget.get_rotation_angle_for_chopper(name, include_guide=False)
    assert rot0 is not None
    assert rot1 is not None

    model = build_rotation_model(chopper)
    expected_delta = direction_to_sign(model.base_spin_direction) * eps
    assert wrap180(rot1 - rot0) == pytest.approx(expected_delta)


def test_widget_spinning_phase_direction_follows_motor_side(qapp):
    widget = ChopperWidget()
    choppers = [
        _canonical("downstream", motor_position="downstream"),
        _canonical("upstream", motor_position="upstream"),
    ]
    widget.update_chopper_data(choppers)

    for name in ("downstream", "upstream"):
        widget.set_chopper_speed(name, 10.0)
        widget.set_chopper_angle(name, 0.0)

    down_0 = widget.get_rotation_angle_for_chopper("downstream")
    up_0 = widget.get_rotation_angle_for_chopper("upstream")

    widget.set_chopper_angle("downstream", 10.0)
    widget.set_chopper_angle("upstream", 10.0)

    down_10 = widget.get_rotation_angle_for_chopper("downstream")
    up_10 = widget.get_rotation_angle_for_chopper("upstream")

    assert _delta(down_10, down_0) == pytest.approx(10.0)
    assert _delta(up_10, up_0) == pytest.approx(10.0)


def test_widget_parked_resolver_direction_follows_motor_side(qapp):
    widget = ChopperWidget()
    choppers = [
        _canonical("downstream", motor_position="downstream"),
        _canonical("upstream", motor_position="upstream"),
    ]
    widget.update_chopper_data(choppers)

    for name in ("downstream", "upstream"):
        widget.set_chopper_speed(name, 0.0)
        widget.set_chopper_angle(name, 0.0)

    down_0 = widget.get_rotation_angle_for_chopper("downstream")
    up_0 = widget.get_rotation_angle_for_chopper("upstream")

    widget.set_chopper_angle("downstream", 10.0)
    widget.set_chopper_angle("upstream", 10.0)

    down_10 = widget.get_rotation_angle_for_chopper("downstream")
    up_10 = widget.get_rotation_angle_for_chopper("upstream")

    assert _delta(down_10, down_0) == pytest.approx(-10.0)
    assert _delta(up_10, up_0) == pytest.approx(10.0)


def test_widget_include_guide_uses_qt_rotation_mapping(qapp):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.update_chopper_data([_canonical("c1")])
    widget.set_chopper_speed("c1", 10.0)
    widget.set_chopper_angle("c1", 5.0)

    base_rotation = widget.get_rotation_angle_for_chopper("c1", include_guide=False)
    qt_rotation = widget.get_rotation_angle_for_chopper("c1", include_guide=True)

    assert qt_rotation == pytest.approx(wrap360(-base_rotation + 270.0))


def test_widget_uses_absolute_speed_threshold_for_motion_state(qapp):
    widget = ChopperWidget()
    widget.update_chopper_data([_canonical("c1")])

    widget.set_chopper_speed("c1", -1.9)
    widget.set_chopper_angle("c1", 10.0)
    parked = widget.get_rotation_angle_for_chopper("c1", include_guide=False)

    widget.set_chopper_speed("c1", -2.1)
    widget.set_chopper_angle("c1", 10.0)
    spinning = widget.get_rotation_angle_for_chopper("c1", include_guide=False)

    assert parked != spinning


def test_widget_ymir_overlap_parked_reference_centers_opening_on_guide(qapp):
    widget = ChopperWidget()
    overlap = _canonical(
        "overlap_chopper",
        slit_edges=[[0.0, 27.6]],
        motor_position="downstream",
        disk_rotation_direction="CCW",
        parked_opening_index=0,
        tdc_resolver_position=0.0,
        park_open_angle=0.0,
        phase_tdc_center_window_delay=0.0,
    )
    widget.update_chopper_data([overlap])
    widget.set_chopper_speed("overlap_chopper", 0.0)
    widget.set_chopper_angle("overlap_chopper", 0.0)

    base = widget.get_rotation_angle_for_chopper(
        "overlap_chopper", include_guide=False
    )
    opening_center = (overlap["slit_edges"][0][0] + overlap["slit_edges"][0][1]) / 2.0
    expected = wrap360(-opening_center)
    assert base == pytest.approx(expected)


@pytest.mark.parametrize("psc", _dream_psc_cases(), ids=lambda p: p["chopper"])
def test_widget_ymir_psc_resolver_alignment_keeps_guide_uncoated_for_each_opening(
    qapp, psc
):
    widget = ChopperWidget()
    chopper_name = psc["chopper"]
    resolver_angles = _resolver_angles_for_all_openings(psc)

    if chopper_name == "pulse_shaping_chopper_1":
        # Known DREAM reference point: opening index 4 is 321.5° on resolver.
        assert resolver_angles[4] == pytest.approx(321.5)

    widget.update_chopper_data([psc])
    widget.set_chopper_speed(chopper_name, 0.0)

    for opening_index, resolver_angle in enumerate(resolver_angles):
        widget.set_chopper_angle(chopper_name, resolver_angle)
        draw_rotation = widget.get_rotation_angle_for_chopper(
            chopper_name, include_guide=True
        )
        assert draw_rotation is not None
        assert not _coating_covers_guide(widget, psc, draw_rotation), (
            f"{chopper_name}: opening index {opening_index} should be centered "
            f"on guide at resolver {resolver_angle:.3f}°, but coating still covers guide"
        )


@pytest.mark.parametrize("psc", _dream_psc_cases(), ids=lambda p: p["chopper"])
def test_widget_ymir_psc_spinning_phase_alignment_keeps_guide_uncoated_for_each_opening(
    qapp, psc
):
    widget = ChopperWidget()
    chopper_name = psc["chopper"]
    speed_hz = 14.0
    phase_angles = _phase_angles_for_all_openings(psc, speed_hz=speed_hz)
    ref_idx = int(psc["parked_opening_index"])

    # Contract: configured phase_tdc_center_window_delay is the spinning
    # reference for the parked opening index.
    assert phase_angles[ref_idx] == pytest.approx(psc["phase_tdc_center_window_delay"])

    widget.update_chopper_data([psc])
    widget.set_chopper_speed(chopper_name, speed_hz)

    for opening_index, phase_angle in enumerate(phase_angles):
        widget.set_chopper_angle(chopper_name, phase_angle)
        draw_rotation = widget.get_rotation_angle_for_chopper(
            chopper_name, include_guide=True
        )
        assert draw_rotation is not None
        assert not _coating_covers_guide(widget, psc, draw_rotation), (
            f"{chopper_name}: opening index {opening_index} should be centered "
            f"on guide at phase {phase_angle:.3f}°, but coating still covers guide"
        )


def test_widget_nmx_wls2_pair_keeps_right_side_open_with_top_bottom_split(qapp):
    # Physical reference (stroboscope): with WLS2A=82.0 and WLS2B=0.0 at 14 Hz
    # both discs are open on the right side, with opposite top/bottom coverage.
    wls2a, wls2b = _nmx_wls2_pair()

    widget = ChopperWidget(guide_pos="DOWN")
    widget.update_chopper_data([wls2a, wls2b])
    widget.set_chopper_speed(wls2a["chopper"], 14.0)
    widget.set_chopper_speed(wls2b["chopper"], 14.0)
    widget.set_chopper_angle(wls2a["chopper"], 82.0)
    widget.set_chopper_angle(wls2b["chopper"], 0.0)

    rot_a = widget.get_rotation_angle_for_chopper(wls2a["chopper"], include_guide=True)
    rot_b = widget.get_rotation_angle_for_chopper(wls2b["chopper"], include_guide=True)
    assert rot_a is not None
    assert rot_b is not None

    open_a = _opening_intervals_qt(wls2a, rot_a)[0]
    open_b = _opening_intervals_qt(wls2b, rot_b)[0]

    # WLS2A: opening on the lower-right side (blade mostly on top).
    assert _interval_contains(300.0, open_a)
    assert not _interval_contains(60.0, open_a)

    # WLS2B: opening on the upper-right side (blade mostly on bottom).
    assert _interval_contains(60.0, open_b)
    assert not _interval_contains(300.0, open_b)
