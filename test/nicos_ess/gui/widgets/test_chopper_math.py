import pytest

from nicos_ess.gui.widgets.chopper_math import (
    CCW,
    CW,
    DOWNSTREAM,
    UPSTREAM,
    ChopperRotationModel,
    build_rotation_model,
    compute_phase_center_delay_deg,
    has_canonical_inputs,
    parked_rotation_deg,
    resolver_direction_sign,
    runtime_phase_sign,
    runtime_spin_sign,
    sign_to_direction,
    spinning_rotation_deg,
    wrap180,
    wrap360,
)
from test.nicos_ess.gui.widgets.chopper_test_fakes import (
    DOWN_GUIDE_ANGLE_DEG,
    fake_double_disc_choppers,
    fake_expected_phase,
    fake_interval_contains,
    fake_opening_intervals_for_base_rotation,
)


def _canonical(**overrides):
    data = {
        "slit_edges": [[0.0, 86.0]],
        "motor_position": DOWNSTREAM,
        "positive_speed_rotation_direction": CW,
        "resolver_positive_direction": CW,
        "parked_opening_index": 0,
        "tdc_resolver_position": 342.5,
        "park_open_angle": 195.0,
        "disk_delay": 0.0,
    }
    data.update(overrides)
    return data


MARKUS_ACTIVE_DISC_CASES = [
    # Values copied from /home/jonas/code/markus_chopper_scripts/*.yaml.
    # Entries with opening=0 are absent discs in Markus' files and are omitted.
    ("BEER FOC-201 upstream", UPSTREAM, CW, 342.0, 221.0, 175.0, 0.0, 239.0),
    ("BIFROST PSC-100 upstream", UPSTREAM, CW, 341.7, 195.0, 170.0, 0.0, 213.3),
    ("BIFROST PSC-100 downstream", DOWNSTREAM, CW, 342.5, 195.0, 170.0, 0.0, 147.5),
    ("DREAM BC-201 upstream", UPSTREAM, CW, 342.0, 153.0, 73.55, 0.0, 171.0),
    ("DREAM PSC-100 upstream disk", DOWNSTREAM, CW, 342.0, 321.5, 5.02, 0.0, 20.5),
    ("DREAM PSC-100 downstream disk", DOWNSTREAM, CW, 342.0, 149.3, 3.94, 0.0, 192.7),
    ("ESTIA BWC-100 upstream disk", DOWNSTREAM, CW, 341.6, 326.0, 100.06, 0.0, 15.6),
    ("HEIMD-TPSC-100 upstream side-window config", UPSTREAM, CW, 341.3, 243.0, 5.2, 5.3, 267.0),
    ("HEIMD-TPSC-100 downstream side-window config", DOWNSTREAM, CW, 341.9, 59.3, 5.2, 6.25, 288.85),
    ("HEIMD-TWSC-101 upstream", UPSTREAM, CW, 342.0, 70.0, 20.0, 0.0, 88.0),
    ("HEIMDAL TPSC-100 upstream", UPSTREAM, CCW, 341.3, 243.0, 5.2, 0.0, 98.3),
    ("HEIMDAL TPSC-100 downstream", DOWNSTREAM, CW, 341.9, 59.3, 5.2, 0.0, 282.6),
    ("HEIMDAL TWSC-101 upstream", UPSTREAM, CW, 342.0, 150.0, 20.0, 0.0, 168.0),
    ("LOKI-FOC-301 downstream", DOWNSTREAM, CCW, 341.9, 239.5, 31.0, 0.0, 257.6),
    ("LOKI-WBC-301 upstream", UPSTREAM, CCW, 341.9, 154.25, 176.5, 0.0, 187.65),
    ("LOKI-WBC-301 downstream", DOWNSTREAM, CCW, 341.9, 154.25, 176.5, 0.0, 172.35),
    ("MAGIC PSC-100 upstream disk", DOWNSTREAM, CW, 341.5, 223.0, 105.0, 0.0, 118.5),
    ("MAGIC PSC-100 downstream disk", DOWNSTREAM, CW, 341.5, 331.5, 105.0, 0.0, 10.0),
    ("MAGIC SC-101 upstream disk", DOWNSTREAM, CW, 342.0, 94.0, 20.6, 0.0, 248.0),
]


def _case_chopper(case):
    _, motor, _markus_effective_dir, tdc, park, opening, disk_delay, _ = case
    return _canonical(
        slit_edges=[[0.0, opening]],
        motor_position=motor,
        positive_speed_rotation_direction=CW,
        resolver_positive_direction=CW,
        tdc_resolver_position=tdc,
        park_open_angle=park,
        disk_delay=disk_delay,
    )


def _spinning(chopper, phase, speed):
    model = build_rotation_model(chopper)
    return spinning_rotation_deg(
        phase,
        speed,
        model.parked_opening_center_deg,
        model.tdc_resolver_position_deg,
        model.park_open_angle_deg,
        model.motor_position,
        model.positive_speed_rotation_direction,
        model.disk_delay_deg,
        model.disk_delay_cw_deg,
        model.disk_delay_ccw_deg,
    )


def test_has_canonical_inputs_requires_slit_edges():
    data = _canonical(slit_edges=[[0.0, 86.0]])
    assert has_canonical_inputs(data)
    assert not has_canonical_inputs(_canonical(slit_edges=None))


@pytest.mark.parametrize(
    ("direction", "motor_position", "expected"),
    [(CW, UPSTREAM, 1), (CCW, UPSTREAM, -1), (CW, DOWNSTREAM, -1), (CCW, DOWNSTREAM, 1)],
)
def test_resolver_direction_sign_is_independent_of_spin_direction(direction, motor_position, expected):
    assert resolver_direction_sign(direction, motor_position) == expected


def test_build_rotation_model_user_example_values():
    model = build_rotation_model(_canonical())

    assert isinstance(model, ChopperRotationModel)
    assert model.positive_speed_rotation_direction == CW
    assert model.resolver_positive_direction == CW
    assert model.resolver_sign == -1
    assert model.parked_opening_center_deg == pytest.approx(43.0)
    assert model.parked_opening_width_deg == pytest.approx(86.0)
    assert model.resolver_offset_deg == pytest.approx(-122.0)
    assert model.phase_tdc_center_window_delay_deg == pytest.approx(147.5)
    assert model.disk_delay_deg == pytest.approx(0.0)


def test_build_rotation_model_validates_optional_park_edges():
    with pytest.raises(ValueError, match="inconsistent"):
        build_rotation_model(_canonical(park_edge_1=120.0, park_edge_2=206.0))


def test_runtime_spin_sign_uses_plc_positive_direction_and_speed_sign():
    assert runtime_spin_sign(10.0, CW) == 1
    assert runtime_spin_sign(-10.0, CW) == -1
    assert runtime_spin_sign(10.0, CCW) == -1
    assert runtime_spin_sign(-10.0, CCW) == 1
    assert runtime_phase_sign(-10.0, CW) == -1


def test_spinning_rotation_positive_phase_moves_opposite_effective_spin():
    chopper = _canonical(tdc_resolver_position=0.0, park_open_angle=0.0)
    assert wrap180(_spinning(chopper, 10.0, 10.0) - _spinning(chopper, 0.0, 10.0)) == pytest.approx(-10.0)
    assert wrap180(_spinning(chopper, 10.0, -10.0) - _spinning(chopper, 0.0, -10.0)) == pytest.approx(10.0)


def test_parked_rotation_resolver_uses_resolver_sign():
    assert parked_rotation_deg(10.0, 5.0, 1) == pytest.approx(15.0)
    assert parked_rotation_deg(10.0, 5.0, -1) == pytest.approx(355.0)


@pytest.mark.parametrize("case", MARKUS_ACTIVE_DISC_CASES, ids=lambda c: c[0])
def test_markus_phase_center_delay_formula_matches_script_values(case):
    _, motor, effective_dir, tdc, park, _, disk_delay, expected = case
    assert compute_phase_center_delay_deg(tdc, park, motor, effective_dir, disk_delay) == pytest.approx(expected)


@pytest.mark.parametrize("case", MARKUS_ACTIVE_DISC_CASES, ids=lambda c: c[0])
def test_markus_park_angle_centers_opening(case):
    chopper = _case_chopper(case)
    model = build_rotation_model(chopper)
    base_rotation = parked_rotation_deg(
        chopper["park_open_angle"], model.resolver_offset_deg, model.resolver_sign
    )
    assert base_rotation == pytest.approx(model.parked_opening_center_deg)


@pytest.mark.parametrize("case", MARKUS_ACTIVE_DISC_CASES, ids=lambda c: c[0])
@pytest.mark.parametrize("effective_dir", [CW, CCW], ids=["effective-cw", "effective-ccw"])
def test_markus_effective_cw_and_ccw_phase_centers_opening(case, effective_dir):
    chopper = _case_chopper(case)
    _, motor, _, tdc, park, _, disk_delay, _ = case
    speed = 14.0 if effective_dir == chopper["positive_speed_rotation_direction"] else -14.0
    phase = compute_phase_center_delay_deg(tdc, park, motor, effective_dir, disk_delay)

    assert _spinning(chopper, phase, speed) == pytest.approx(
        build_rotation_model(chopper).parked_opening_center_deg
    )


def test_nonzero_parked_opening_index_is_allowed():
    model = build_rotation_model(
        _canonical(
            slit_edges=[[0.0, 2.46], [171.52, 176.54], [272.865, 276.795]],
            parked_opening_index=1,
            park_open_angle=321.5,
            tdc_resolver_position=342.0,
        )
    )
    assert model.parked_opening_index == 1
    assert model.parked_opening_width_deg == pytest.approx(5.02)


def test_phase_delay_reference_aligns_parked_opening_while_spinning():
    chopper = _canonical(
        slit_edges=[[0.0, 2.46], [171.52, 176.54], [272.865, 276.795]],
        parked_opening_index=1,
        park_open_angle=321.5,
        tdc_resolver_position=342.0,
    )
    model = build_rotation_model(chopper)
    assert _spinning(chopper, model.phase_tdc_center_window_delay_deg, 14.0) == pytest.approx(
        model.parked_opening_center_deg
    )


def test_phase_perturbation_moves_opposite_runtime_phase_direction():
    chopper = _canonical()
    model = build_rotation_model(chopper)
    eps = 0.2
    rot0 = _spinning(chopper, model.phase_tdc_center_window_delay_deg, 14.0)
    rot1 = _spinning(chopper, model.phase_tdc_center_window_delay_deg + eps, 14.0)
    assert wrap180(rot1 - rot0) == pytest.approx(
        -runtime_phase_sign(14.0, model.positive_speed_rotation_direction) * eps
    )


def test_resolver_perturbation_uses_resolver_polarity_not_spin_direction():
    chopper = _canonical()
    model = build_rotation_model(chopper)
    eps = 0.2
    rot0 = parked_rotation_deg(chopper["park_open_angle"], model.resolver_offset_deg, model.resolver_sign)
    rot1 = parked_rotation_deg(chopper["park_open_angle"] + eps, model.resolver_offset_deg, model.resolver_sign)
    assert wrap180(rot1 - rot0) == pytest.approx(model.resolver_sign * eps)


def test_nmx_wls2_pair_has_small_transmitted_opening_on_right_at_82_and_0():
    # Preserved NMX physical reference: WLS2A/WLS2B at 14 Hz with phases
    # 82 deg / 0 deg shows a small transmission on the right.
    wls2a = _canonical(
        slit_edges=[[0.0, 170.0]],
        motor_position=UPSTREAM,
        positive_speed_rotation_direction=CW,
        tdc_resolver_position=341.7,
        park_open_angle=73.0,
    )
    wls2b = _canonical(
        slit_edges=[[0.0, 170.0]],
        motor_position=DOWNSTREAM,
        positive_speed_rotation_direction=CW,
        tdc_resolver_position=342.5,
        park_open_angle=165.0,
    )

    def opening_interval_qt(chopper, phase_deg):
        qt_rotation = wrap360(_spinning(chopper, phase_deg, 14.0) + 270.0)
        start, end = chopper["slit_edges"][0]
        return wrap360(-float(end) + qt_rotation), wrap360(-float(start) + qt_rotation)

    def unwrap(interval):
        start, end = interval
        if end < start:
            return [(start, 360.0), (0.0, end)]
        return [(start, end)]

    transmitted = []
    for s1, e1 in unwrap(opening_interval_qt(wls2a, 82.0)):
        for s2, e2 in unwrap(opening_interval_qt(wls2b, 0.0)):
            lo = max(s1, s2)
            hi = min(e1, e2)
            if hi > lo:
                transmitted.append((lo, hi))

    assert transmitted
    assert sum(hi - lo for lo, hi in transmitted) <= 8.0
    assert any(lo <= 10.0 or hi >= 350.0 for lo, hi in transmitted)


def test_fake_double_disc_parked_open_angle_opens_beam_for_both_discs():
    for chopper in fake_double_disc_choppers():
        model = build_rotation_model(chopper)
        base_rotation = parked_rotation_deg(180.0, model.resolver_offset_deg, model.resolver_sign)
        intervals = fake_opening_intervals_for_base_rotation(chopper, base_rotation)
        assert fake_interval_contains(DOWN_GUIDE_ANGLE_DEG, intervals[0])


def test_fake_double_disc_parked_close_angle_closes_beam_for_both_discs():
    for chopper in fake_double_disc_choppers():
        model = build_rotation_model(chopper)
        base_rotation = parked_rotation_deg(0.0, model.resolver_offset_deg, model.resolver_sign)
        intervals = fake_opening_intervals_for_base_rotation(chopper, base_rotation)
        assert not any(fake_interval_contains(DOWN_GUIDE_ANGLE_DEG, interval) for interval in intervals)


@pytest.mark.parametrize("disc_index", [0, 1], ids=["disc1", "disc2"])
@pytest.mark.parametrize("speed_hz", [14.0, -14.0], ids=["positive", "negative"])
@pytest.mark.parametrize("opening_index", [0, 1], ids=["opening0", "opening1"])
def test_fake_double_disc_tdc_opening_delay_order_follows_physical_rotation(
    disc_index, speed_hz, opening_index
):
    chopper = fake_double_disc_choppers()[disc_index]
    expected_phase = fake_expected_phase(chopper, speed_hz, opening_index)
    model = build_rotation_model(chopper)
    base_rotation = _spinning(chopper, expected_phase, speed_hz)
    intervals = fake_opening_intervals_for_base_rotation(chopper, base_rotation)
    assert fake_interval_contains(DOWN_GUIDE_ANGLE_DEG, intervals[opening_index])
    assert sign_to_direction(runtime_spin_sign(speed_hz, model.positive_speed_rotation_direction)) in (CW, CCW)
