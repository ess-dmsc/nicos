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
Qt = qt.Qt
from nicos_ess.gui.widgets.chopper_math import (
    CCW,
    CW,
    build_rotation_model,
    compute_phase_center_delay_deg,
    disk_delay_for_direction,
    opening_center_deg,
    runtime_phase_sign,
    wrap180,
    wrap360,
)
from nicos_ess.gui.widgets.chopper_widget import ChopperWidget
from test.nicos_ess.gui.widgets.chopper_test_fakes import (
    DOWN_GUIDE_ANGLE_DEG,
    fake_double_disc_choppers,
    fake_expected_phase,
)


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
        "positive_speed_rotation_direction": CW,
        "resolver_positive_direction": CW,
        "parked_opening_index": 0,
        "tdc_resolver_position": 60.0,
        "park_open_angle": 30.0,
        "disk_delay": 0.0,
    }
    data.update(overrides)
    return data


def _delta(after, before):
    return wrap180(after - before)


def _ymir_psc(name, **overrides):
    """Canonical PSC inputs copied from `ymir/setups/choppers_dream.py`."""
    return _canonical(name, **overrides)


def _first_guide_hits_by_opening(
    widget, chopper, speed_hz, resolution_deg=0.1
) -> dict[int, tuple[float, float] | None]:
    """Find best-centered scan angle where each opening covers the beam guide.

    This is intentionally widget-driven (scan over user-set angle) instead of
    inverting the same math used for rendering, to avoid tautological tests.
    """
    chopper_name = chopper["chopper"]
    slit_edges = chopper["slit_edges"]
    hits = {idx: None for idx in range(len(slit_edges))}
    best_margins = {idx: -1.0 for idx in range(len(slit_edges))}

    def _interval_margin(angle, interval):
        if not _interval_contains(angle, interval):
            return -1.0
        start, end = interval
        ang = angle
        if end < start:
            end += 360.0
            if ang < start:
                ang += 360.0
        return min(ang - start, end - ang)

    widget.update_chopper_data([chopper])
    widget.set_chopper_speed(chopper_name, speed_hz)

    nsteps = int(round(360.0 / resolution_deg))
    for step in range(nsteps):
        user_angle = (step * resolution_deg) % 360.0
        widget.set_chopper_angle(chopper_name, user_angle)
        draw_rotation = widget.get_rotation_angle_for_chopper(
            chopper_name, include_guide=True
        )
        assert draw_rotation is not None

        opening_intervals = _opening_intervals_qt(chopper, draw_rotation)
        for opening_index, interval in enumerate(opening_intervals):
            margin = _interval_margin(widget._guide_angle_deg, interval)
            if margin < 0.0:
                continue
            if _coating_covers_guide(widget, chopper, draw_rotation):
                continue
            if margin > best_margins[opening_index]:
                best_margins[opening_index] = margin
                hits[opening_index] = (user_angle, draw_rotation)

    return hits


def _opening_centers(chopper: dict) -> list[float]:
    return [opening_center_deg(edges) for edges in chopper["slit_edges"]]


def _resolver_angles_for_all_openings_from_reference(chopper: dict) -> dict[int, float]:
    """Resolver setpoints derived from park reference and opening centers."""
    centers = _opening_centers(chopper)
    ref_idx = int(chopper["parked_opening_index"])
    ref_center = centers[ref_idx]
    ref_resolver = float(chopper["park_open_angle"])
    model = build_rotation_model(chopper)
    return {
        opening_index: wrap360(
            ref_resolver + model.resolver_sign * wrap180(center - ref_center)
        )
        for opening_index, center in enumerate(centers)
    }


def _phase_angles_for_all_openings_from_reference(
    chopper: dict, speed_hz: float
) -> dict[int, float]:
    """Phase setpoints derived from phase-delay reference and opening centers."""
    centers = _opening_centers(chopper)
    ref_idx = int(chopper["parked_opening_index"])
    ref_center = centers[ref_idx]
    model = build_rotation_model(chopper)
    spin_sign = runtime_phase_sign(speed_hz, model.positive_speed_rotation_direction)
    effective_direction = CW if spin_sign >= 0 else CCW
    ref_phase = compute_phase_center_delay_deg(
        model.tdc_resolver_position_deg,
        model.park_open_angle_deg,
        model.motor_position,
        effective_direction,
        disk_delay_for_direction(
            effective_direction,
            model.disk_delay_deg,
            model.disk_delay_cw_deg,
            model.disk_delay_ccw_deg,
        ),
    )
    return {
        opening_index: wrap360(ref_phase - spin_sign * wrap180(center - ref_center))
        for opening_index, center in enumerate(centers)
    }


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


def _rendered_guide_probe_is_dark(widget, qapp) -> bool:
    """Render widget and check whether the guide probe pixel is dark/coated."""
    widget.resize(420, 420)
    qapp.processEvents()

    pixmap = QPixmap(widget.size())
    pixmap.fill(Qt.GlobalColor.white)
    widget.render(pixmap)
    image = pixmap.toImage()

    positions, chopper_radius = widget.calculate_positions(len(widget.chopper_data))
    assert positions
    center = positions[0]

    slit_height = chopper_radius * 0.3
    reduced_radius = chopper_radius - slit_height
    inner_coating = reduced_radius + chopper_radius * 0.05
    outer_coating = chopper_radius * 0.95
    guide_probe_radius = (inner_coating + outer_coating) / 2.0

    guide_theta = radians(widget._guide_angle_deg)
    probe_x = int(round(center.x() + guide_probe_radius * cos(guide_theta)))
    probe_y = int(round(center.y() - guide_probe_radius * sin(guide_theta)))

    dark_samples = 0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            sx = min(max(probe_x + dx, 0), image.width() - 1)
            sy = min(max(probe_y + dy, 0), image.height() - 1)
            color = image.pixelColor(sx, sy)
            if color.red() < 50 and color.green() < 50 and color.blue() < 50:
                dark_samples += 1

    return dark_samples >= 5


def _rendered_probe_is_dark(widget, qapp, probe_angle_deg: float) -> bool:
    """Render widget and check whether one ring probe angle is dark/coated."""
    widget.resize(420, 420)
    qapp.processEvents()

    pixmap = QPixmap(widget.size())
    pixmap.fill(Qt.GlobalColor.white)
    widget.render(pixmap)
    image = pixmap.toImage()

    positions, chopper_radius = widget.calculate_positions(len(widget.chopper_data))
    assert positions
    center = positions[0]

    slit_height = chopper_radius * 0.3
    reduced_radius = chopper_radius - slit_height
    inner_coating = reduced_radius + chopper_radius * 0.05
    outer_coating = chopper_radius * 0.95
    probe_radius = (inner_coating + outer_coating) / 2.0

    theta = radians(float(probe_angle_deg))
    probe_x = int(round(center.x() + probe_radius * cos(theta)))
    probe_y = int(round(center.y() - probe_radius * sin(theta)))

    dark_samples = 0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            sx = min(max(probe_x + dx, 0), image.width() - 1)
            sy = min(max(probe_y + dy, 0), image.height() - 1)
            color = image.pixelColor(sx, sy)
            if color.red() < 50 and color.green() < 50 and color.blue() < 50:
                dark_samples += 1

    return dark_samples >= 5


def _rendered_has_opening_near_angle(
    widget, qapp, target_angle_deg: float, half_window_deg: float = 12.0
) -> bool:
    """True when at least one probe near target angle is non-dark/open."""
    probe_angle = target_angle_deg - half_window_deg
    while probe_angle <= target_angle_deg + half_window_deg + 1e-9:
        if not _rendered_probe_is_dark(widget, qapp, probe_angle):
            return True
        probe_angle += 1.0
    return False


def _rendered_opening_centered_at_guide(
    widget, qapp, inside_offset_deg: float = 70.0, outside_offset_deg: float = 100.0
) -> bool:
    guide = float(widget._guide_angle_deg)
    # For 170° WLS openings centered on guide, +/-70° should be open and
    # +/-100° should be coated.
    inside_open = (
        not _rendered_probe_is_dark(widget, qapp, guide + inside_offset_deg)
        and not _rendered_probe_is_dark(widget, qapp, guide - inside_offset_deg)
    )
    outside_dark = (
        _rendered_probe_is_dark(widget, qapp, guide + outside_offset_deg)
        and _rendered_probe_is_dark(widget, qapp, guide - outside_offset_deg)
    )
    return inside_open and outside_dark


def _opening_intervals_qt(chopper, rotation_angle):
    """Opening intervals in widget Qt-angle coordinates for one chopper."""
    intervals = []
    for start, end in chopper["slit_edges"]:
        intervals.append(
            (
                wrap360(-float(end) + rotation_angle),
                wrap360(-float(start) + rotation_angle),
            )
        )
    return intervals


def _interval_contains(angle, interval):
    angle = wrap360(angle)
    start, end = interval
    if end < start:
        return angle >= start or angle <= end
    return start <= angle <= end


def _unwrap_interval(interval):
    start, end = interval
    if end < start:
        return [(start, 360.0), (0.0, end)]
    return [(start, end)]


def _combined_transmitted_intervals(*opening_groups):
    transmitted = [
        segment
        for interval in opening_groups[0]
        for segment in _unwrap_interval(interval)
    ]
    for opening_group in opening_groups[1:]:
        next_transmitted = []
        unwrapped_group = [
            segment
            for interval in opening_group
            for segment in _unwrap_interval(interval)
        ]
        for s1, e1 in transmitted:
            for s2, e2 in unwrapped_group:
                lo = max(s1, s2)
                hi = min(e1, e2)
                if hi > lo:
                    next_transmitted.append((lo, hi))
        transmitted = next_transmitted
    return transmitted


def _interval_center(interval):
    start, end = interval
    return wrap360(start + wrap360(end - start) / 2.0)


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
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        tdc_resolver_position=342.0,
        park_open_angle=321.5,
        disk_delay=0.0,
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
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        tdc_resolver_position=342.0,
        park_open_angle=49.3,
        disk_delay=0.0,
    )
    return [psc1, psc2]


def _nmx_wls2_pair():
    # Values taken from `nicos_ess/nmx/setups/wls2a_chopper.py` and
    # `nicos_ess/nmx/setups/wls2b_chopper.py`.
    wls2a = _canonical(
        "wls2a",
        slit_edges=[[0.0, 170.0]],
        motor_position="upstream",
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        parked_opening_index=0,
        tdc_resolver_position=341.7,
        park_open_angle=73.0,
        disk_delay=0.0,
    )
    wls2b = _canonical(
        "wls2b",
        slit_edges=[[0.0, 170.0]],
        motor_position="downstream",
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        parked_opening_index=0,
        tdc_resolver_position=342.5,
        park_open_angle=165.0,
        disk_delay=0.0,
    )
    return wls2a, wls2b


def _nmx_wls_cases():
    wls1 = _canonical(
        "wls1",
        slit_edges=[[0.0, 170.0]],
        motor_position="downstream",
        positive_speed_rotation_direction="CCW",
        resolver_positive_direction=CW,
        parked_opening_index=0,
        tdc_resolver_position=342.5,
        park_open_angle=5.0,
        disk_delay=-70.0,
        legacy_phase_reference=-47.5,
    )
    wls2a, wls2b = _nmx_wls2_pair()
    return [wls1, wls2a, wls2b]


def _heimdal_tpsc_pair():
    # Values from the HEIMDAL-ChpSy1 TPSC-100 pair.  Markus' park values
    # 243.0 and 59.3 are transparent-window references; the canonical
    # park_open_angle values here are the corresponding DOWN beam-guide
    # references.
    tpsc101 = _canonical(
        "tpsc101",
        slit_edges=[[0.0, 5.20]],
        motor_position="upstream",
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        parked_opening_index=0,
        tdc_resolver_position=341.3,
        park_open_angle=333.0,
        park_edge_1=330.4,
        park_edge_2=335.6,
        disk_delay_cw=185.3,
        disk_delay_ccw=186.6,
        left_window_ccw_center_delay=104.9,
        left_window_park_resolver_angle=243.0,
        down_park_resolver_angle=333.0,
    )
    tpsc102 = _canonical(
        "tpsc102",
        slit_edges=[[0.0, 5.20]],
        motor_position="downstream",
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        parked_opening_index=0,
        tdc_resolver_position=341.9,
        park_open_angle=329.3,
        park_edge_1=326.7,
        park_edge_2=331.9,
        disk_delay_cw=186.25,
        disk_delay_ccw=185.5,
        left_window_ccw_center_delay=82.9,
        left_window_park_resolver_angle=59.3,
        down_park_resolver_angle=329.3,
    )
    return [tpsc101, tpsc102]


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
    assert widget.get_spin_direction_sign_for_chopper("downstream") == 1
    assert widget.get_spin_direction_sign_for_chopper("upstream") == 1

    widget.set_chopper_speed("downstream", -10.0)
    widget.set_chopper_speed("upstream", -10.0)
    assert widget.get_spin_direction_sign_for_chopper("downstream") == -1
    assert widget.get_spin_direction_sign_for_chopper("upstream") == -1


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
    model = build_rotation_model(chopper)
    phase0 = model.phase_tdc_center_window_delay_deg

    widget.set_chopper_speed(name, speed_hz)
    widget.set_chopper_angle(name, phase0)
    rot0 = widget.get_rotation_angle_for_chopper(name, include_guide=False)
    widget.set_chopper_angle(name, phase0 + eps)
    rot1 = widget.get_rotation_angle_for_chopper(name, include_guide=False)
    assert rot0 is not None
    assert rot1 is not None

    expected_delta = -runtime_phase_sign(
        speed_hz, model.positive_speed_rotation_direction
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
    phase0 = build_rotation_model(chopper).phase_tdc_center_window_delay_deg

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
    # Qt's CCW-positive sense. Same visual motion therefore maps to -arrow_sign.
    assert wrap180(rot1 - rot0) == pytest.approx(-arrow_sign * eps)


@pytest.mark.parametrize(
    "chopper",
    [
        _canonical("downstream", motor_position="downstream"),
        _canonical("upstream", motor_position="upstream"),
    ],
    ids=lambda c: c["chopper"],
)
def test_widget_resolver_perturbation_uses_resolver_polarity(qapp, chopper):
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
    expected_delta = model.resolver_sign * eps
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

    down_model = build_rotation_model(choppers[0])
    up_model = build_rotation_model(choppers[1])

    expected_down = -runtime_phase_sign(
        10.0, down_model.positive_speed_rotation_direction
    ) * 10.0
    expected_up = -runtime_phase_sign(
        10.0, up_model.positive_speed_rotation_direction
    ) * 10.0

    assert _delta(down_10, down_0) == pytest.approx(expected_down)
    assert _delta(up_10, up_0) == pytest.approx(expected_up)


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

    down_model = build_rotation_model(choppers[0])
    up_model = build_rotation_model(choppers[1])

    expected_down = down_model.resolver_sign * 10.0
    expected_up = up_model.resolver_sign * 10.0

    assert _delta(down_10, down_0) == pytest.approx(expected_down)
    assert _delta(up_10, up_0) == pytest.approx(expected_up)


def test_widget_include_guide_uses_qt_rotation_mapping(qapp):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.update_chopper_data([_canonical("c1")])
    widget.set_chopper_speed("c1", 10.0)
    widget.set_chopper_angle("c1", 5.0)

    base_rotation = widget.get_rotation_angle_for_chopper("c1", include_guide=False)
    qt_rotation = widget.get_rotation_angle_for_chopper("c1", include_guide=True)

    assert qt_rotation == pytest.approx(wrap360(base_rotation + 270.0))


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
        positive_speed_rotation_direction="CCW",
        resolver_positive_direction=CW,
        parked_opening_index=0,
        tdc_resolver_position=0.0,
        park_open_angle=0.0,
        disk_delay=0.0,
    )
    widget.update_chopper_data([overlap])
    widget.set_chopper_speed("overlap_chopper", 0.0)
    widget.set_chopper_angle("overlap_chopper", 0.0)

    base = widget.get_rotation_angle_for_chopper(
        "overlap_chopper", include_guide=False
    )
    opening_center = (overlap["slit_edges"][0][0] + overlap["slit_edges"][0][1]) / 2.0
    expected = wrap360(opening_center)
    assert base == pytest.approx(expected)


@pytest.mark.parametrize("psc", _dream_psc_cases(), ids=lambda p: p["chopper"])
def test_widget_choppers_dream_psc_resolver_alignment_keeps_guide_uncoated_for_each_opening(
    qapp, psc
):
    widget = ChopperWidget(guide_pos="DOWN")
    chopper_name = psc["chopper"]
    guide_hits = _first_guide_hits_by_opening(widget, psc, speed_hz=0.0)
    missing_indices = [
        opening_index
        for opening_index, hit in guide_hits.items()
        if hit is None
    ]
    assert not missing_indices, (
        f"{chopper_name}: parked scan could not place guide in openings "
        f"{missing_indices}; widget rendering/angle mapping is inconsistent"
    )

    for opening_index, hit in guide_hits.items():
        resolver_angle, draw_rotation = hit
        assert not _coating_covers_guide(widget, psc, draw_rotation), (
            f"{chopper_name}: opening index {opening_index} should be centered "
            f"on guide at resolver {resolver_angle:.3f}°, but coating still covers guide"
        )


@pytest.mark.parametrize("psc", _dream_psc_cases(), ids=lambda p: p["chopper"])
def test_widget_choppers_dream_psc_spinning_phase_alignment_keeps_guide_uncoated_for_each_opening(
    qapp, psc
):
    widget = ChopperWidget(guide_pos="DOWN")
    chopper_name = psc["chopper"]
    guide_hits = _first_guide_hits_by_opening(widget, psc, speed_hz=14.0)
    missing_indices = [
        opening_index
        for opening_index, hit in guide_hits.items()
        if hit is None
    ]
    assert not missing_indices, (
        f"{chopper_name}: spinning scan could not place guide in openings "
        f"{missing_indices}; widget rendering/phase mapping is inconsistent"
    )

    for opening_index, hit in guide_hits.items():
        phase_angle, draw_rotation = hit
        assert not _coating_covers_guide(widget, psc, draw_rotation), (
            f"{chopper_name}: opening index {opening_index} should be centered "
            f"on guide at phase {phase_angle:.3f}°, but coating still covers guide"
        )


@pytest.mark.parametrize("psc", _dream_psc_cases(), ids=lambda p: p["chopper"])
def test_widget_choppers_dream_psc_park_open_reference_renders_open_at_down_guide(
    qapp, psc
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper_name = psc["chopper"]
    widget.update_chopper_data([psc])
    widget.set_chopper_speed(chopper_name, 0.0)
    widget.set_chopper_angle(chopper_name, float(psc["park_open_angle"]))
    assert not _rendered_guide_probe_is_dark(widget, qapp), (
        f"{chopper_name}: expected an opening at park_open_angle="
        f"{float(psc['park_open_angle']):.3f}°, but rendered blade/coating at guide"
    )


@pytest.mark.parametrize("psc", _dream_psc_cases(), ids=lambda p: p["chopper"])
def test_widget_choppers_dream_psc_phase_reference_renders_open_at_down_guide(
    qapp, psc
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper_name = psc["chopper"]
    phase_ref = build_rotation_model(psc).phase_tdc_center_window_delay_deg
    widget.update_chopper_data([psc])
    widget.set_chopper_speed(chopper_name, 14.0)
    widget.set_chopper_angle(chopper_name, phase_ref)
    assert not _rendered_guide_probe_is_dark(widget, qapp), (
        f"{chopper_name}: expected an opening at computed center-window phase="
        f"{phase_ref:.3f}°, "
        "but rendered blade/coating at guide"
    )


def test_widget_choppers_dream_psc1_spinning_phase_20_5_renders_open_at_down_guide(
    qapp,
):
    psc1 = _dream_psc_cases()[0]
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper_name = psc1["chopper"]
    widget.update_chopper_data([psc1])
    widget.set_chopper_speed(chopper_name, 14.0)
    widget.set_chopper_angle(chopper_name, 20.5)
    assert not _rendered_guide_probe_is_dark(widget, qapp), (
        f"{chopper_name}: expected opening at spinning phase 20.5°, "
        "but rendered blade/coating at DOWN guide"
    )


@pytest.mark.parametrize("psc", _dream_psc_cases(), ids=lambda p: p["chopper"])
def test_widget_choppers_dream_psc_all_openings_render_open_at_down_guide_parked(
    qapp, psc
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper_name = psc["chopper"]
    resolver_angles = _resolver_angles_for_all_openings_from_reference(psc)

    for opening_index, resolver_angle in resolver_angles.items():
        widget.update_chopper_data([psc])
        widget.set_chopper_speed(chopper_name, 0.0)
        widget.set_chopper_angle(chopper_name, resolver_angle)
        assert not _rendered_guide_probe_is_dark(widget, qapp), (
            f"{chopper_name}: opening index {opening_index} at parked angle "
            f"{resolver_angle:.3f}° renders coated at DOWN guide"
        )


@pytest.mark.parametrize("psc", _dream_psc_cases(), ids=lambda p: p["chopper"])
def test_widget_choppers_dream_psc_all_openings_render_open_at_down_guide_spinning(
    qapp, psc
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper_name = psc["chopper"]
    phase_angles = _phase_angles_for_all_openings_from_reference(psc, speed_hz=14.0)

    for opening_index, phase_angle in phase_angles.items():
        widget.update_chopper_data([psc])
        widget.set_chopper_speed(chopper_name, 14.0)
        widget.set_chopper_angle(chopper_name, phase_angle)
        assert not _rendered_guide_probe_is_dark(widget, qapp), (
            f"{chopper_name}: opening index {opening_index} at spinning phase "
            f"{phase_angle:.3f}° renders coated at DOWN guide"
        )


@pytest.mark.parametrize("tpsc", _heimdal_tpsc_pair(), ids=lambda c: c["chopper"])
def test_widget_heimdal_tpsc_parked_resolver_table_centers_opening_on_down(
    qapp, tpsc
):
    widget = ChopperWidget(guide_pos="DOWN")
    chopper_name = tpsc["chopper"]
    widget.update_chopper_data([tpsc])
    widget.set_chopper_speed(chopper_name, 0.0)
    widget.set_chopper_angle(chopper_name, float(tpsc["down_park_resolver_angle"]))

    draw_rotation = widget.get_rotation_angle_for_chopper(
        chopper_name, include_guide=True
    )
    assert draw_rotation is not None
    opening_center = _interval_center(_opening_intervals_qt(tpsc, draw_rotation)[0])

    assert wrap180(opening_center - widget._guide_angle_deg) == pytest.approx(0.0)


@pytest.mark.parametrize("tpsc", _heimdal_tpsc_pair(), ids=lambda c: c["chopper"])
def test_widget_heimdal_tpsc_parked_resolver_table_renders_opening_on_down(
    qapp, tpsc
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper_name = tpsc["chopper"]
    widget.update_chopper_data([tpsc])
    widget.set_chopper_speed(chopper_name, 0.0)
    widget.set_chopper_angle(chopper_name, float(tpsc["down_park_resolver_angle"]))

    assert not _rendered_probe_is_dark(widget, qapp, widget._guide_angle_deg), (
        f"{chopper_name}: expected opening at DOWN guide for parked resolver "
        f"angle {float(tpsc['down_park_resolver_angle']):.1f}°, "
        "but rendered blade/coating there"
    )
    assert _rendered_probe_is_dark(widget, qapp, widget._guide_angle_deg + 12.0)
    assert _rendered_probe_is_dark(widget, qapp, widget._guide_angle_deg - 12.0)


@pytest.mark.parametrize("tpsc", _heimdal_tpsc_pair(), ids=lambda c: c["chopper"])
def test_widget_heimdal_tpsc_transparent_window_resolver_centers_opening_on_left(
    qapp, tpsc
):
    widget = ChopperWidget(guide_pos="DOWN")
    chopper_name = tpsc["chopper"]
    widget.update_chopper_data([tpsc])
    widget.set_chopper_speed(chopper_name, 0.0)
    parked_left_angle = float(tpsc["left_window_park_resolver_angle"])
    widget.set_chopper_angle(chopper_name, parked_left_angle)

    draw_rotation = widget.get_rotation_angle_for_chopper(
        chopper_name, include_guide=True
    )
    assert draw_rotation is not None
    opening_center = _interval_center(_opening_intervals_qt(tpsc, draw_rotation)[0])

    assert wrap180(opening_center - widget._guide_angle_deg) == pytest.approx(-90.0)
    assert wrap180(opening_center - 180.0) == pytest.approx(0.0)


@pytest.mark.parametrize("tpsc", _heimdal_tpsc_pair(), ids=lambda c: c["chopper"])
def test_widget_heimdal_tpsc_transparent_window_resolver_renders_opening_on_left(
    qapp, tpsc
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper_name = tpsc["chopper"]
    widget.update_chopper_data([tpsc])
    widget.set_chopper_speed(chopper_name, 0.0)
    widget.set_chopper_angle(
        chopper_name, float(tpsc["left_window_park_resolver_angle"])
    )

    assert not _rendered_probe_is_dark(widget, qapp, 180.0), (
        f"{chopper_name}: expected opening at left-side window for parked "
        f"resolver angle {float(tpsc['left_window_park_resolver_angle']):.1f}°, "
        "but rendered blade/coating there"
    )
    assert _rendered_probe_is_dark(widget, qapp, 168.0)
    assert _rendered_probe_is_dark(widget, qapp, 192.0)


@pytest.mark.parametrize("tpsc", _heimdal_tpsc_pair(), ids=lambda c: c["chopper"])
def test_widget_heimdal_tpsc_effective_ccw_phase_centers_opening_on_left(
    qapp, tpsc
):
    widget = ChopperWidget(guide_pos="DOWN")
    chopper_name = tpsc["chopper"]
    ccw_center_delay = float(tpsc["left_window_ccw_center_delay"])
    widget.update_chopper_data([tpsc])
    widget.set_chopper_speed(chopper_name, -14.0)
    widget.set_chopper_angle(chopper_name, ccw_center_delay)

    draw_rotation = widget.get_rotation_angle_for_chopper(
        chopper_name, include_guide=True
    )
    assert draw_rotation is not None
    opening_center = _interval_center(_opening_intervals_qt(tpsc, draw_rotation)[0])

    assert wrap180(opening_center - widget._guide_angle_deg) == pytest.approx(-90.0)
    assert wrap180(opening_center - 180.0) == pytest.approx(0.0)


@pytest.mark.parametrize("tpsc", _heimdal_tpsc_pair(), ids=lambda c: c["chopper"])
def test_widget_heimdal_tpsc_effective_ccw_phase_renders_opening_on_left(
    qapp, tpsc
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper_name = tpsc["chopper"]
    ccw_center_delay = float(tpsc["left_window_ccw_center_delay"])
    widget.update_chopper_data([tpsc])
    widget.set_chopper_speed(chopper_name, -14.0)
    widget.set_chopper_angle(chopper_name, ccw_center_delay)

    assert not _rendered_probe_is_dark(widget, qapp, 180.0), (
        f"{chopper_name}: expected opening at left-side window for effective "
        f"CCW phase {ccw_center_delay:.1f}°, but rendered blade/coating there"
    )
    assert _rendered_probe_is_dark(widget, qapp, 168.0)
    assert _rendered_probe_is_dark(widget, qapp, 192.0)


def test_widget_heimdal_tpsc_pair_effective_ccw_phases_show_left_side_transmission(
    qapp,
):
    tpsc101, tpsc102 = _heimdal_tpsc_pair()
    widget = ChopperWidget(guide_pos="DOWN")
    widget.update_chopper_data([tpsc101, tpsc102])

    for tpsc in (tpsc101, tpsc102):
        chopper_name = tpsc["chopper"]
        widget.set_chopper_speed(chopper_name, -14.0)
        widget.set_chopper_angle(
            chopper_name, float(tpsc["left_window_ccw_center_delay"])
        )

    intervals = []
    for tpsc in (tpsc101, tpsc102):
        draw_rotation = widget.get_rotation_angle_for_chopper(
            tpsc["chopper"], include_guide=True
        )
        assert draw_rotation is not None
        intervals.append(_opening_intervals_qt(tpsc, draw_rotation)[0])

    transmitted_opening = []
    for s1, e1 in _unwrap_interval(intervals[0]):
        for s2, e2 in _unwrap_interval(intervals[1]):
            lo = max(s1, s2)
            hi = min(e1, e2)
            if hi > lo:
                transmitted_opening.append((lo, hi))

    assert transmitted_opening
    total_opening = sum(hi - lo for lo, hi in transmitted_opening)
    assert total_opening == pytest.approx(5.2)
    assert any(lo <= 180.0 <= hi for lo, hi in transmitted_opening)


@pytest.mark.parametrize(
    ("disc1_speed", "disc2_speed"),
    [
        (14.0, -14.0),
        (-14.0, 14.0),
        (14.0, 14.0),
        (-14.0, -14.0),
    ],
    ids=["disc1-pos-disc2-neg", "disc1-neg-disc2-pos", "both-pos", "both-neg"],
)
@pytest.mark.parametrize(
    ("opening_index", "expected_width"),
    [(0, 40.0), (1, 20.0)],
    ids=["opening0", "opening1"],
)
def test_widget_fake_double_disc_matrix_transmission_contains_down_guide(
    qapp, disc1_speed, disc2_speed, opening_index, expected_width
):
    disc1, disc2 = fake_double_disc_choppers()
    widget = ChopperWidget(guide_pos="DOWN")
    widget.update_chopper_data([disc1, disc2])

    for chopper, speed_hz in ((disc1, disc1_speed), (disc2, disc2_speed)):
        widget.set_chopper_speed(chopper["chopper"], speed_hz)
        widget.set_chopper_angle(
            chopper["chopper"],
            fake_expected_phase(chopper, speed_hz, opening_index),
        )

    opening_groups = []
    for chopper in (disc1, disc2):
        draw_rotation = widget.get_rotation_angle_for_chopper(
            chopper["chopper"], include_guide=True
        )
        assert draw_rotation is not None
        opening_intervals = _opening_intervals_qt(chopper, draw_rotation)
        assert _interval_contains(
            DOWN_GUIDE_ANGLE_DEG, opening_intervals[opening_index]
        )
        opening_groups.append(opening_intervals)

    transmitted = _combined_transmitted_intervals(*opening_groups)
    guide_segments = [
        (lo, hi) for lo, hi in transmitted if lo <= DOWN_GUIDE_ANGLE_DEG <= hi
    ]

    assert guide_segments
    assert sum(hi - lo for lo, hi in guide_segments) == pytest.approx(expected_width)


def test_widget_nmx_wls2_pair_shows_small_right_side_transmission_opening(qapp):
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

    # Right-side opening edge should be close to 0° on each disc.
    assert min(abs(wrap180(open_a[0])), abs(wrap180(open_a[1]))) <= 8.0
    assert min(abs(wrap180(open_b[0])), abs(wrap180(open_b[1]))) <= 8.0

    # Pair contract: combined transmitted opening is a small window on right.
    a_start, a_end = open_a
    b_start, b_end = open_b

    def _unwrap(interval):
        start, end = interval
        if end < start:
            return [(start, 360.0), (0.0, end)]
        return [(start, end)]

    transmitted_opening = []
    for s1, e1 in _unwrap((a_start, a_end)):
        for s2, e2 in _unwrap((b_start, b_end)):
            lo = max(s1, s2)
            hi = min(e1, e2)
            if hi > lo:
                transmitted_opening.append((lo, hi))

    assert transmitted_opening
    total_opening = sum(hi - lo for lo, hi in transmitted_opening)
    assert total_opening <= 8.0
    assert any(lo <= 10.0 or hi >= 350.0 for lo, hi in transmitted_opening)


def test_widget_nmx_wls2_pair_direction_contract(qapp):
    wls2a, wls2b = _nmx_wls2_pair()
    widget = ChopperWidget(guide_pos="DOWN")
    widget.update_chopper_data([wls2a, wls2b])

    for name, phase0 in (("wls2a", 82.0), ("wls2b", 0.0)):
        eps = 0.2
        widget.set_chopper_speed(name, 14.0)
        assert widget.get_spin_direction_sign_for_chopper(name) == 1

        widget.set_chopper_angle(name, phase0)
        rot0 = widget.get_rotation_angle_for_chopper(name, include_guide=True)
        widget.set_chopper_angle(name, phase0 + eps)
        rot1 = widget.get_rotation_angle_for_chopper(name, include_guide=True)
        assert rot0 is not None
        assert rot1 is not None
        chopper = wls2a if name == "wls2a" else wls2b
        model = build_rotation_model(chopper)
        expected_delta = -runtime_phase_sign(
            14.0, model.positive_speed_rotation_direction
        ) * eps
        assert wrap180(rot1 - rot0) == pytest.approx(expected_delta)

        widget.set_chopper_speed(name, 0.0)
        widget.set_chopper_angle(name, 10.0)
        park0 = widget.get_rotation_angle_for_chopper(name, include_guide=True)
        widget.set_chopper_angle(name, 10.0 + eps)
        park1 = widget.get_rotation_angle_for_chopper(name, include_guide=True)
        assert park0 is not None
        assert park1 is not None
        # Resolver perturbation direction is canonical-bookkeeping dependent.
        assert abs(wrap180(park1 - park0)) == pytest.approx(eps)


@pytest.mark.parametrize(
    ("chopper_name", "phase_deg"),
    [("wls2a", 82.0), ("wls2b", 0.0)],
)
def test_widget_nmx_wls2_disc_renders_opening_near_furthest_right(
    qapp, chopper_name, phase_deg
):
    wls2a, wls2b = _nmx_wls2_pair()
    chopper = wls2a if chopper_name == "wls2a" else wls2b

    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    widget.update_chopper_data([chopper])
    widget.set_chopper_speed(chopper_name, 14.0)
    widget.set_chopper_angle(chopper_name, phase_deg)

    # Physical contract: at WLS2A/WLS2B phases 82°/0°, each disc has an opening
    # edge close to the furthest right side (0° in widget angle convention).
    assert _rendered_has_opening_near_angle(widget, qapp, target_angle_deg=0.0), (
        f"{chopper_name}: expected rendered opening near right side at phase "
        f"{phase_deg:.1f}°, but found only blade/coating there"
    )


@pytest.mark.parametrize("wls", _nmx_wls_cases(), ids=lambda c: c["chopper"])
def test_widget_nmx_wls_phase_reference_renders_centered_opening_at_down_guide(
    qapp, wls
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    name = wls["chopper"]
    phase_ref = build_rotation_model(wls).phase_tdc_center_window_delay_deg

    widget.update_chopper_data([wls])
    widget.set_chopper_speed(name, 14.0)
    widget.set_chopper_angle(name, phase_ref)

    assert not _rendered_guide_probe_is_dark(widget, qapp), (
        f"{name}: expected rendered opening at guide for spinning phase reference "
        f"{phase_ref:.3f}°, but guide probe is coated"
    )
    assert _rendered_opening_centered_at_guide(widget, qapp), (
        f"{name}: expected opening centered around DOWN guide at phase "
        f"{phase_ref:.3f}° (inside probes open, outside probes coated)"
    )
