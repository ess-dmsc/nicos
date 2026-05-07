# ruff: noqa: E402

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
from nicos_ess.gui.widgets.chopper_math import (
    CCW,
    CW,
    DOWNSTREAM,
    UPSTREAM,
    build_rotation_model,
    compute_phase_center_delay_deg,
    opening_center_deg,
    opening_width_deg,
    runtime_spin_sign,
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
        "motor_position": DOWNSTREAM,
        "positive_speed_rotation_direction": CW,
        "resolver_positive_direction": CW,
        "parked_opening_index": 0,
        "tdc_resolver_position": 60.0,
        "park_open_angle": 30.0,
        "disk_delay": 0.0,
    }
    data.update(overrides)
    return data


def _rendered_probe_is_dark(widget, qapp, probe_angle_deg: float) -> bool:
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


def _rendered_guide_probe_is_dark(widget, qapp) -> bool:
    return _rendered_probe_is_dark(widget, qapp, widget._guide_angle_deg)


def _assert_rendered_opening_centered(
    widget,
    qapp,
    *,
    center_angle_deg: float,
    inside_offset_deg: float,
    outside_offset_deg: float,
):
    assert not _rendered_probe_is_dark(widget, qapp, center_angle_deg)
    assert not _rendered_probe_is_dark(
        widget, qapp, center_angle_deg + inside_offset_deg
    )
    assert not _rendered_probe_is_dark(
        widget, qapp, center_angle_deg - inside_offset_deg
    )
    assert _rendered_probe_is_dark(widget, qapp, center_angle_deg + outside_offset_deg)
    assert _rendered_probe_is_dark(widget, qapp, center_angle_deg - outside_offset_deg)


def _rendered_has_opening_near_angle(
    widget, qapp, target_angle_deg: float, half_window_deg: float = 8.0
) -> bool:
    probe_angle = target_angle_deg - half_window_deg
    while probe_angle <= target_angle_deg + half_window_deg + 1e-9:
        if not _rendered_probe_is_dark(widget, qapp, probe_angle):
            return True
        probe_angle += 1.0
    return False


def _opening_intervals_qt(chopper, rotation_angle):
    return [
        (wrap360(-float(end) + rotation_angle), wrap360(-float(start) + rotation_angle))
        for start, end in chopper["slit_edges"]
    ]


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


def _phase_reference(chopper: dict, speed_hz: float) -> float:
    model = build_rotation_model(chopper)
    spin_sign = runtime_spin_sign(speed_hz, model.positive_speed_rotation_direction)
    effective_direction = CW if spin_sign >= 0 else CCW
    phase = compute_phase_center_delay_deg(
        model.tdc_resolver_position_deg,
        model.park_open_angle_deg,
        model.motor_position,
        effective_direction,
        model.disk_delay_deg,
    )
    if spin_sign != (1 if model.positive_speed_rotation_direction == CW else -1):
        phase = wrap360(phase + 180.0)
    return phase


def _resolver_angles_for_all_openings_from_reference(chopper: dict) -> dict[int, float]:
    centers = [opening_center_deg(edges) for edges in chopper["slit_edges"]]
    ref_idx = int(chopper["parked_opening_index"])
    ref_center = centers[ref_idx]
    model = build_rotation_model(chopper)
    return {
        idx: wrap360(
            float(chopper["park_open_angle"])
            + model.resolver_sign * wrap180(center - ref_center)
        )
        for idx, center in enumerate(centers)
    }


def _phase_angles_for_all_openings_from_reference(
    chopper: dict, speed_hz: float
) -> dict[int, float]:
    centers = [opening_center_deg(edges) for edges in chopper["slit_edges"]]
    ref_idx = int(chopper["parked_opening_index"])
    ref_center = centers[ref_idx]
    spin_sign = runtime_spin_sign(
        speed_hz, build_rotation_model(chopper).positive_speed_rotation_direction
    )
    ref_phase = _phase_reference(chopper, speed_hz)
    return {
        idx: wrap360(ref_phase - spin_sign * wrap180(center - ref_center))
        for idx, center in enumerate(centers)
    }


def _dream_psc_cases():
    psc1 = _canonical(
        "dream_psc1",
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
        motor_position=DOWNSTREAM,
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        tdc_resolver_position=342.0,
        park_open_angle=321.5,
    )
    psc2 = _canonical(
        "dream_psc2",
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
        motor_position=DOWNSTREAM,
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        tdc_resolver_position=342.0,
        park_open_angle=49.3,
    )
    return [psc1, psc2]


def _nmx_wls2_pair():
    wls2a = _canonical(
        "wls2a",
        slit_edges=[[0.0, 170.0]],
        motor_position=UPSTREAM,
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        tdc_resolver_position=341.7,
        park_open_angle=73.0,
    )
    wls2b = _canonical(
        "wls2b",
        slit_edges=[[0.0, 170.0]],
        motor_position=DOWNSTREAM,
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        tdc_resolver_position=342.5,
        park_open_angle=165.0,
    )
    return wls2a, wls2b


def _nmx_wls_cases():
    wls1 = _canonical(
        "wls1",
        slit_edges=[[0.0, 86.0]],
        motor_position=DOWNSTREAM,
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        tdc_resolver_position=342.5,
        park_open_angle=195.0,
    )
    wls2a, wls2b = _nmx_wls2_pair()
    return [wls1, wls2a, wls2b]


def _heimdal_tpsc_pair():
    tpsc101 = _canonical(
        "tpsc101",
        slit_edges=[[0.0, 5.20]],
        motor_position=UPSTREAM,
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        tdc_resolver_position=341.3,
        park_open_angle=333.0,
        disk_delay=6.6,
        left_window_ccw_center_delay=104.9,
        left_window_park_resolver_angle=243.0,
        down_park_resolver_angle=333.0,
    )
    tpsc102 = _canonical(
        "tpsc102",
        slit_edges=[[0.0, 5.20]],
        motor_position=DOWNSTREAM,
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        tdc_resolver_position=341.9,
        park_open_angle=329.3,
        disk_delay=5.5,
        left_window_ccw_center_delay=82.9,
        left_window_park_resolver_angle=59.3,
        down_park_resolver_angle=329.3,
    )
    return [tpsc101, tpsc102]


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


@pytest.mark.parametrize(
    ("motor_position", "resolver_direction"),
    [
        (UPSTREAM, CW),
        (UPSTREAM, CCW),
        (DOWNSTREAM, CW),
        (DOWNSTREAM, CCW),
    ],
)
def test_generic_single_opening_parked_reference_renders_open_at_down_guide(
    qapp, motor_position, resolver_direction
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper = _canonical(
        "single",
        slit_edges=[[0.0, 90.0]],
        motor_position=motor_position,
        resolver_positive_direction=resolver_direction,
        park_open_angle=123.0,
    )

    widget.update_chopper_data([chopper])
    widget.set_chopper_speed("single", 0.0)
    widget.set_chopper_angle("single", 123.0)

    _assert_rendered_opening_centered(
        widget,
        qapp,
        center_angle_deg=widget._guide_angle_deg,
        inside_offset_deg=30.0,
        outside_offset_deg=55.0,
    )


@pytest.mark.parametrize(
    ("motor_position", "positive_direction", "speed_hz"),
    [
        (UPSTREAM, CW, 14.0),
        (UPSTREAM, CW, -14.0),
        (DOWNSTREAM, CW, 14.0),
        (DOWNSTREAM, CCW, 14.0),
    ],
)
def test_generic_single_opening_phase_reference_renders_open_at_down_guide(
    qapp, motor_position, positive_direction, speed_hz
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper = _canonical(
        "single",
        slit_edges=[[0.0, 90.0]],
        motor_position=motor_position,
        positive_speed_rotation_direction=positive_direction,
        tdc_resolver_position=60.0,
        park_open_angle=30.0,
    )

    widget.update_chopper_data([chopper])
    widget.set_chopper_speed("single", speed_hz)
    widget.set_chopper_angle("single", _phase_reference(chopper, speed_hz))

    _assert_rendered_opening_centered(
        widget,
        qapp,
        center_angle_deg=widget._guide_angle_deg,
        inside_offset_deg=30.0,
        outside_offset_deg=55.0,
    )


def test_generic_single_opening_phase_perturbation_moves_rendered_opening(
    qapp,
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    speed_hz = 14.0
    chopper = _canonical("single", slit_edges=[[0.0, 12.0]])
    phase_ref = _phase_reference(chopper, speed_hz)

    widget.update_chopper_data([chopper])
    widget.set_chopper_speed("single", speed_hz)
    widget.set_chopper_angle("single", phase_ref + 25.0)

    assert _rendered_guide_probe_is_dark(widget, qapp)
    assert _rendered_has_opening_near_angle(
        widget, qapp, widget._guide_angle_deg - 25.0
    )


@pytest.mark.parametrize(
    ("motor_position", "resolver_direction", "expected_shift"),
    [
        (UPSTREAM, CW, 25.0),
        (DOWNSTREAM, CW, -25.0),
    ],
)
def test_generic_single_opening_resolver_perturbation_moves_rendered_opening(
    qapp, motor_position, resolver_direction, expected_shift
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper = _canonical(
        "single",
        slit_edges=[[0.0, 12.0]],
        motor_position=motor_position,
        resolver_positive_direction=resolver_direction,
        park_open_angle=123.0,
    )

    widget.update_chopper_data([chopper])
    widget.set_chopper_speed("single", 0.0)
    widget.set_chopper_angle("single", 148.0)

    assert _rendered_guide_probe_is_dark(widget, qapp)
    assert _rendered_has_opening_near_angle(
        widget, qapp, widget._guide_angle_deg + expected_shift
    )


def test_generic_multi_opening_index_zero_can_park_all_windows_at_down_guide(qapp):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper = _canonical(
        "multi_idx0",
        slit_edges=[[0.0, 20.0], [90.0, 120.0], [250.0, 310.0]],
        motor_position=UPSTREAM,
        resolver_positive_direction=CW,
        parked_opening_index=0,
        park_open_angle=180.0,
    )

    widget.update_chopper_data([chopper])
    widget.set_chopper_speed("multi_idx0", 0.0)
    for resolver_angle in (180.0, 275.0, 90.0):
        widget.set_chopper_angle("multi_idx0", resolver_angle)
        assert not _rendered_guide_probe_is_dark(widget, qapp)


def test_generic_multi_opening_index_zero_can_phase_all_windows_at_down_guide(qapp):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper = _canonical(
        "multi_idx0",
        slit_edges=[[0.0, 20.0], [90.0, 120.0], [250.0, 310.0]],
        motor_position=UPSTREAM,
        positive_speed_rotation_direction=CW,
        parked_opening_index=0,
        tdc_resolver_position=60.0,
        park_open_angle=180.0,
    )

    widget.update_chopper_data([chopper])
    widget.set_chopper_speed("multi_idx0", 14.0)
    for phase_angle in (120.0, 25.0, 210.0):
        widget.set_chopper_angle("multi_idx0", phase_angle)
        assert not _rendered_guide_probe_is_dark(widget, qapp)


def test_generic_multi_opening_nonzero_index_can_park_all_windows_at_down_guide(
    qapp,
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper = _canonical(
        "multi_idx2",
        slit_edges=[[0.0, 20.0], [90.0, 110.0], [245.0, 275.0]],
        motor_position=DOWNSTREAM,
        resolver_positive_direction=CW,
        parked_opening_index=2,
        park_open_angle=40.0,
    )

    widget.update_chopper_data([chopper])
    widget.set_chopper_speed("multi_idx2", 0.0)
    for resolver_angle in (290.0, 200.0, 40.0):
        widget.set_chopper_angle("multi_idx2", resolver_angle)
        assert not _rendered_guide_probe_is_dark(widget, qapp)


def test_generic_multi_opening_nonzero_index_can_phase_all_windows_at_down_guide(
    qapp,
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    chopper = _canonical(
        "multi_idx2",
        slit_edges=[[0.0, 20.0], [90.0, 110.0], [245.0, 275.0]],
        motor_position=DOWNSTREAM,
        positive_speed_rotation_direction=CW,
        parked_opening_index=2,
        tdc_resolver_position=20.0,
        park_open_angle=40.0,
        disk_delay=7.0,
    )

    widget.update_chopper_data([chopper])
    widget.set_chopper_speed("multi_idx2", 14.0)
    for phase_angle in (237.0, 147.0, 347.0):
        widget.set_chopper_angle("multi_idx2", phase_angle)
        assert not _rendered_guide_probe_is_dark(widget, qapp)


@pytest.mark.parametrize("psc", _dream_psc_cases(), ids=lambda c: c["chopper"])
def test_widget_dream_psc_park_reference_renders_open_at_down_guide(qapp, psc):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    widget.update_chopper_data([psc])
    widget.set_chopper_speed(psc["chopper"], 0.0)
    widget.set_chopper_angle(psc["chopper"], float(psc["park_open_angle"]))

    assert not _rendered_guide_probe_is_dark(widget, qapp)


@pytest.mark.parametrize(
    ("psc", "phase_angle"),
    [
        (_dream_psc_cases()[0], 20.5),
        (_dream_psc_cases()[1], 292.7),
    ],
    ids=["dream_psc1", "dream_psc2"],
)
def test_widget_dream_psc_phase_reference_renders_open_at_down_guide(
    qapp, psc, phase_angle
):
    widget = ChopperWidget(guide_pos="DOWN")
    widget.set_show_guide_line(False)
    widget.update_chopper_data([psc])
    widget.set_chopper_speed(psc["chopper"], 14.0)
    widget.set_chopper_angle(psc["chopper"], phase_angle)

    assert not _rendered_guide_probe_is_dark(widget, qapp)


def test_widget_dream_psc_all_openings_can_be_parked_at_down_guide(qapp):
    for psc in _dream_psc_cases():
        widget = ChopperWidget(guide_pos="DOWN")
        widget.set_show_guide_line(False)
        widget.update_chopper_data([psc])
        widget.set_chopper_speed(psc["chopper"], 0.0)

        resolver_angles = _resolver_angles_for_all_openings_from_reference(psc)
        for opening_index, resolver_angle in resolver_angles.items():
            widget.set_chopper_angle(psc["chopper"], resolver_angle)
            assert not _rendered_guide_probe_is_dark(widget, qapp), (
                f"{psc['chopper']} opening {opening_index} rendered coated "
                f"at parked angle {resolver_angle:.3f}"
            )


def test_widget_dream_psc_all_openings_can_be_phased_at_down_guide(qapp):
    for psc in _dream_psc_cases():
        widget = ChopperWidget(guide_pos="DOWN")
        widget.set_show_guide_line(False)
        widget.update_chopper_data([psc])
        widget.set_chopper_speed(psc["chopper"], 14.0)

        for opening_index, phase_angle in _phase_angles_for_all_openings_from_reference(
            psc, speed_hz=14.0
        ).items():
            widget.set_chopper_angle(psc["chopper"], phase_angle)
            assert not _rendered_guide_probe_is_dark(widget, qapp), (
                f"{psc['chopper']} opening {opening_index} rendered coated "
                f"at spinning phase {phase_angle:.3f}"
            )


def test_widget_nmx_wls2_pair_shows_small_right_side_transmission_opening(qapp):
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
    transmitted_opening = _combined_transmitted_intervals([open_a], [open_b])

    assert transmitted_opening
    assert min(abs(wrap180(open_a[0])), abs(wrap180(open_a[1]))) <= 8.0
    assert min(abs(wrap180(open_b[0])), abs(wrap180(open_b[1]))) <= 8.0
    assert sum(hi - lo for lo, hi in transmitted_opening) <= 8.0
    assert any(lo <= 10.0 or hi >= 350.0 for lo, hi in transmitted_opening)


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

    assert _rendered_has_opening_near_angle(widget, qapp, target_angle_deg=0.0)


def test_widget_nmx_wls_phase_reference_renders_centered_opening_at_down_guide(
    qapp,
):
    for wls in _nmx_wls_cases():
        widget = ChopperWidget(guide_pos="DOWN")
        widget.set_show_guide_line(False)
        width = opening_width_deg(wls["slit_edges"][0])
        inside_offset = min(width * 0.4, 70.0)
        outside_offset = width / 2.0 + 15.0

        widget.update_chopper_data([wls])
        widget.set_chopper_speed(wls["chopper"], 14.0)
        widget.set_chopper_angle(wls["chopper"], _phase_reference(wls, 14.0))

        _assert_rendered_opening_centered(
            widget,
            qapp,
            center_angle_deg=widget._guide_angle_deg,
            inside_offset_deg=inside_offset,
            outside_offset_deg=outside_offset,
        )


def test_widget_heimdal_tpsc_renders_down_park_opening(qapp):
    for tpsc in _heimdal_tpsc_pair():
        widget = ChopperWidget(guide_pos="DOWN")
        widget.set_show_guide_line(False)
        widget.update_chopper_data([tpsc])
        widget.set_chopper_speed(tpsc["chopper"], 0.0)
        widget.set_chopper_angle(
            tpsc["chopper"], float(tpsc["down_park_resolver_angle"])
        )

        assert not _rendered_probe_is_dark(widget, qapp, widget._guide_angle_deg)
        assert _rendered_probe_is_dark(widget, qapp, widget._guide_angle_deg + 12.0)
        assert _rendered_probe_is_dark(widget, qapp, widget._guide_angle_deg - 12.0)


def test_widget_heimdal_tpsc_renders_left_transparent_window(qapp):
    for tpsc in _heimdal_tpsc_pair():
        widget = ChopperWidget(guide_pos="DOWN")
        widget.set_show_guide_line(False)
        widget.update_chopper_data([tpsc])
        widget.set_chopper_speed(tpsc["chopper"], 0.0)
        widget.set_chopper_angle(
            tpsc["chopper"], float(tpsc["left_window_park_resolver_angle"])
        )

        assert not _rendered_probe_is_dark(widget, qapp, 180.0)
        assert _rendered_probe_is_dark(widget, qapp, 168.0)
        assert _rendered_probe_is_dark(widget, qapp, 192.0)


def test_widget_heimdal_tpsc_renders_left_effective_ccw_phase(qapp):
    for tpsc in _heimdal_tpsc_pair():
        widget = ChopperWidget(guide_pos="DOWN")
        widget.set_show_guide_line(False)
        widget.update_chopper_data([tpsc])
        widget.set_chopper_speed(tpsc["chopper"], -14.0)
        widget.set_chopper_angle(
            tpsc["chopper"], float(tpsc["left_window_ccw_center_delay"])
        )

        assert not _rendered_probe_is_dark(widget, qapp, 180.0)
        assert _rendered_probe_is_dark(widget, qapp, 168.0)
        assert _rendered_probe_is_dark(widget, qapp, 192.0)


def test_widget_heimdal_tpsc_pair_effective_ccw_phases_show_left_side_transmission(
    qapp,
):
    tpsc101, tpsc102 = _heimdal_tpsc_pair()
    widget = ChopperWidget(guide_pos="DOWN")
    widget.update_chopper_data([tpsc101, tpsc102])

    for tpsc in (tpsc101, tpsc102):
        widget.set_chopper_speed(tpsc["chopper"], -14.0)
        widget.set_chopper_angle(
            tpsc["chopper"], float(tpsc["left_window_ccw_center_delay"])
        )

    intervals = []
    for tpsc in (tpsc101, tpsc102):
        draw_rotation = widget.get_rotation_angle_for_chopper(
            tpsc["chopper"], include_guide=True
        )
        assert draw_rotation is not None
        intervals.append(_opening_intervals_qt(tpsc, draw_rotation)[0])

    transmitted_opening = _combined_transmitted_intervals(
        [intervals[0]], [intervals[1]]
    )

    assert transmitted_opening
    assert sum(hi - lo for lo, hi in transmitted_opening) == pytest.approx(5.2)
    assert any(lo <= 180.0 <= hi for lo, hi in transmitted_opening)
