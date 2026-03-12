import pytest

from nicos_ess.gui.widgets.chopper_math import (
    CCW,
    CW,
    ChopperRotationModel,
    apply_motor_side_transform,
    build_rotation_model,
    direction_to_sign,
    has_canonical_inputs,
    parked_rotation_deg,
    runtime_phase_sign,
    runtime_spin_sign,
    spinning_rotation_deg,
    wrap180,
    wrap360,
)


def _canonical(**overrides):
    data = {
        "slit_edges": [[0.0, 86.0]],
        "motor_position": "downstream",
        "disk_rotation_direction": "CW",
        "parked_opening_index": 0,
        "tdc_resolver_position": 342.5,
        "park_open_angle": 195.0,
        "phase_tdc_center_window_delay": 147.5,
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    ("direction", "motor_position", "expected"),
    [
        (CW, "downstream", CCW),
        (CCW, "downstream", CW),
        (CW, "upstream", CW),
        (CCW, "upstream", CCW),
    ],
)
def test_apply_motor_side_transform(direction, motor_position, expected):
    assert apply_motor_side_transform(direction, motor_position) == expected


def test_has_canonical_inputs_does_not_require_park_edges():
    assert has_canonical_inputs(_canonical())


def test_build_rotation_model_user_example_values():
    model = build_rotation_model(_canonical())

    assert isinstance(model, ChopperRotationModel)
    assert model.base_spin_direction == CCW
    assert model.phase_reference_sign == -1
    assert model.parked_opening_center_deg == pytest.approx(43.0)
    assert model.parked_opening_width_deg == pytest.approx(86.0)
    assert model.resolver_offset_deg == pytest.approx(-122.0)
    assert model.spin_offset_deg == pytest.approx(-169.5)
    assert model.expected_phase_delay_deg == pytest.approx(147.5)
    assert model.phase_delay_error_deg == pytest.approx(0.0)


def test_build_rotation_model_validates_optional_park_edges():
    with pytest.raises(ValueError, match="inconsistent"):
        build_rotation_model(
            _canonical(
                park_edge_1=120.0,
                park_edge_2=206.0,
            )
        )


def test_runtime_spin_sign_uses_base_direction_and_speed_sign():
    assert runtime_spin_sign(10.0, CW) == 1
    assert runtime_spin_sign(-10.0, CW) == -1
    assert runtime_spin_sign(10.0, CCW) == -1
    assert runtime_spin_sign(-10.0, CCW) == 1


def test_runtime_phase_sign_includes_phase_reference_sign():
    assert runtime_phase_sign(10.0, CW, 1) == 1
    assert runtime_phase_sign(10.0, CW, -1) == -1
    assert runtime_phase_sign(10.0, CCW, 1) == -1
    assert runtime_phase_sign(10.0, CCW, -1) == 1


def test_spinning_rotation_positive_phase_opposite_spin():
    assert spinning_rotation_deg(10.0, 10.0, 0.0, CW) == pytest.approx(350.0)
    assert spinning_rotation_deg(10.0, 10.0, 0.0, CCW) == pytest.approx(10.0)


def test_parked_rotation_resolver_follows_base_direction():
    assert parked_rotation_deg(10.0, 5.0, CW) == pytest.approx(355.0)
    assert parked_rotation_deg(10.0, 5.0, CCW) == pytest.approx(15.0)


def test_phase_delay_wrap_error():
    model = build_rotation_model(
        _canonical(
            tdc_resolver_position=10.0,
            park_open_angle=350.0,
            phase_tdc_center_window_delay=15.0,
        )
    )
    assert model.expected_phase_delay_deg == pytest.approx(20.0)
    assert wrap180(model.phase_delay_error_deg) == pytest.approx(-5.0)


def test_phase_delay_reference_uses_motor_side_sign():
    model = build_rotation_model(
        _canonical(
            motor_position="upstream",
            tdc_resolver_position=341.7,
            park_open_angle=73.0,
            phase_tdc_center_window_delay=91.3,
        )
    )
    assert model.expected_phase_delay_deg == pytest.approx(91.3)
    assert model.phase_delay_error_deg == pytest.approx(0.0)
    assert model.phase_reference_sign == 1


def test_build_rotation_model_requires_parked_opening_start_at_zero():
    with pytest.raises(ValueError, match="slit_edges must start at 0 degrees"):
        build_rotation_model(_canonical(slit_edges=[[5.0, 91.0]]))


def test_park_open_angle_aligns_opening_center_with_beam_guide():
    model = build_rotation_model(
        _canonical(
            slit_edges=[[0.0, 27.6]],
            disk_rotation_direction="CCW",
            motor_position="downstream",
            park_open_angle=0.0,
            tdc_resolver_position=0.0,
            phase_tdc_center_window_delay=0.0,
        )
    )
    center = model.parked_opening_center_deg
    parked_at_reference = parked_rotation_deg(
        resolver_angle_deg=0.0,
        resolver_offset_deg=model.resolver_offset_deg,
        base_spin_direction=model.base_spin_direction,
        phase_reference_sign=model.phase_reference_sign,
    )
    assert parked_at_reference == pytest.approx(center)


def test_nonzero_parked_opening_index_is_allowed():
    model = build_rotation_model(
        _canonical(
            slit_edges=[[0.0, 2.46], [171.52, 176.54], [272.865, 276.795]],
            parked_opening_index=1,
            park_open_angle=321.5,
            tdc_resolver_position=342.0,
            phase_tdc_center_window_delay=20.5,
        )
    )
    assert model.parked_opening_index == 1
    assert model.parked_opening_width_deg == pytest.approx(5.02)


def test_phase_delay_reference_aligns_parked_opening_while_spinning():
    model = build_rotation_model(
        _canonical(
            slit_edges=[[0.0, 2.46], [171.52, 176.54], [272.865, 276.795]],
            parked_opening_index=1,
            park_open_angle=321.5,
            tdc_resolver_position=342.0,
            phase_tdc_center_window_delay=20.5,
        )
    )
    opening_center = model.parked_opening_center_deg
    spinning_at_phase_reference = spinning_rotation_deg(
        phase_angle_deg=20.5,
        speed_hz=14.0,
        spin_offset_deg=model.spin_offset_deg,
        base_spin_direction=model.base_spin_direction,
        phase_reference_sign=model.phase_reference_sign,
    )
    expected_base = opening_center
    assert spinning_at_phase_reference == pytest.approx(expected_base)


@pytest.mark.parametrize(
    "chopper",
    [
        _canonical(),
        _canonical(
            motor_position="upstream",
            tdc_resolver_position=341.7,
            park_open_angle=73.0,
            phase_tdc_center_window_delay=91.3,
        ),
    ],
    ids=["downstream", "upstream"],
)
def test_phase_perturbation_moves_opposite_runtime_phase_direction(chopper):
    model = build_rotation_model(chopper)
    eps = 0.2
    phase0 = float(chopper["phase_tdc_center_window_delay"])
    rot0 = spinning_rotation_deg(
        phase0,
        14.0,
        model.spin_offset_deg,
        model.base_spin_direction,
        model.phase_reference_sign,
    )
    rot1 = spinning_rotation_deg(
        phase0 + eps,
        14.0,
        model.spin_offset_deg,
        model.base_spin_direction,
        model.phase_reference_sign,
    )
    expected_delta = -runtime_phase_sign(
        14.0, model.base_spin_direction, model.phase_reference_sign
    ) * eps
    assert wrap180(rot1 - rot0) == pytest.approx(expected_delta)


@pytest.mark.parametrize(
    "chopper",
    [
        _canonical(),
        _canonical(
            motor_position="upstream",
            tdc_resolver_position=341.7,
            park_open_angle=73.0,
            phase_tdc_center_window_delay=91.3,
        ),
    ],
    ids=["downstream", "upstream"],
)
def test_resolver_perturbation_moves_with_base_spin_direction(chopper):
    model = build_rotation_model(chopper)
    eps = 0.2
    resolver0 = float(chopper["park_open_angle"])
    rot0 = parked_rotation_deg(
        resolver0,
        model.resolver_offset_deg,
        model.base_spin_direction,
        model.phase_reference_sign,
    )
    rot1 = parked_rotation_deg(
        resolver0 + eps,
        model.resolver_offset_deg,
        model.base_spin_direction,
        model.phase_reference_sign,
    )
    expected_delta = (
        -direction_to_sign(model.base_spin_direction)
        * int(model.phase_reference_sign)
        * eps
    )
    assert wrap180(rot1 - rot0) == pytest.approx(expected_delta)


def test_nmx_wls2_pair_has_small_transmitted_opening_on_right_at_82_and_0():
    # Physical reference: standing at target and looking towards sample,
    # WLS2A/WLS2B at 14 Hz with phases 82°/0° shows a small opening on right.
    wls2a = {
        "slit_edges": [[0.0, 170.0]],
        "motor_position": "upstream",
        "disk_rotation_direction": "CW",
        "parked_opening_index": 0,
        "tdc_resolver_position": 341.7,
        "park_open_angle": 73.0,
        "phase_tdc_center_window_delay": 91.3,
    }
    wls2b = {
        "slit_edges": [[0.0, 170.0]],
        "motor_position": "downstream",
        "disk_rotation_direction": "CW",
        "parked_opening_index": 0,
        "tdc_resolver_position": 342.5,
        "park_open_angle": 165.0,
        "phase_tdc_center_window_delay": 177.5,
    }

    def opening_interval_qt(chopper, phase_deg):
        model = build_rotation_model(chopper)
        base_rotation = spinning_rotation_deg(
            phase_deg,
            14.0,
            model.spin_offset_deg,
            model.base_spin_direction,
            model.phase_reference_sign,
        )
        qt_rotation = wrap360(base_rotation + 270.0)
        start, end = chopper["slit_edges"][0]
        return wrap360(-float(end) + qt_rotation), wrap360(-float(start) + qt_rotation)

    def unwrap(interval):
        start, end = interval
        if end < start:
            return [(start, 360.0), (0.0, end)]
        return [(start, end)]

    open_a = opening_interval_qt(wls2a, 82.0)
    open_b = opening_interval_qt(wls2b, 0.0)

    transmitted_opening = []
    for s1, e1 in unwrap(open_a):
        for s2, e2 in unwrap(open_b):
            lo = max(s1, s2)
            hi = min(e1, e2)
            if hi > lo:
                transmitted_opening.append((lo, hi))

    assert transmitted_opening
    total_width = sum(hi - lo for lo, hi in transmitted_opening)
    assert total_width <= 8.0
    assert any(lo <= 10.0 or hi >= 350.0 for lo, hi in transmitted_opening)
