import pytest

from nicos_ess.gui.widgets.chopper_math import (
    CCW,
    CW,
    DOWNSTREAM,
    UPSTREAM,
    ChopperRotationModel,
    build_rotation_model,
    compute_phase_center_delay_deg,
    disk_delay_for_rotation,
    opening_center_deg,
    opening_width_deg,
    parked_rotation_deg,
    resolver_direction_sign,
    runtime_spin_sign,
    spinning_rotation_deg,
    wrap180,
)


def _canonical(**overrides):
    data = {
        "slit_edges": [[0.0, 90.0]],
        "motor_position": DOWNSTREAM,
        "positive_speed_rotation_direction": CW,
        "resolver_positive_direction": CW,
        "parked_opening_index": 0,
        "tdc_resolver_position": 60.0,
        "park_open_angle": 30.0,
        "guide_position": "DOWN",
        "disk_delay": 0.0,
    }
    data.update(overrides)
    return data


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
        model.resolver_positive_direction,
        model.disk_delay_deg,
        model.cw_disk_delay_deg,
        model.ccw_disk_delay_deg,
    )


@pytest.mark.parametrize(
    ("direction", "motor_position", "expected"),
    [
        (CW, UPSTREAM, 1),
        (CCW, UPSTREAM, -1),
        (CW, DOWNSTREAM, -1),
        (CCW, DOWNSTREAM, 1),
    ],
)
def test_resolver_direction_sign_combines_resolver_polarity_and_motor_side(
    direction, motor_position, expected
):
    assert resolver_direction_sign(direction, motor_position) == expected


@pytest.mark.parametrize(
    ("speed", "positive_direction", "expected"),
    [
        (14.0, CW, 1),
        (-14.0, CW, -1),
        (14.0, CCW, -1),
        (-14.0, CCW, 1),
    ],
)
def test_runtime_spin_sign_maps_speed_sign_to_effective_direction(
    speed, positive_direction, expected
):
    assert runtime_spin_sign(speed, positive_direction) == expected


@pytest.mark.parametrize(
    ("motor_position", "effective_direction", "expected"),
    [
        (UPSTREAM, CW, 338.0),
        (DOWNSTREAM, CW, 28.0),
    ],
)
def test_compute_phase_center_delay_deg_uses_motor_side_and_effective_spin_branch(
    motor_position, effective_direction, expected
):
    assert compute_phase_center_delay_deg(
        tdc_resolver_position=20.0,
        park_open_angle=355.0,
        motor_position=motor_position,
        effective_rotation_direction=effective_direction,
        disk_delay_deg=3.0,
    ) == pytest.approx(expected)


def test_build_rotation_model_uses_nonzero_parked_opening_index():
    chopper = _canonical(
        slit_edges=[[0.0, 20.0], [90.0, 130.0], [250.0, 300.0]],
        motor_position=UPSTREAM,
        resolver_positive_direction=CCW,
        parked_opening_index=2,
        park_open_angle=40.0,
        tdc_resolver_position=12.0,
    )

    model = build_rotation_model(chopper)

    assert isinstance(model, ChopperRotationModel)
    assert model.parked_opening_center_deg == pytest.approx(275.0)
    assert model.resolver_sign == -1
    assert model.resolver_offset_deg == pytest.approx(-45.0)
    assert parked_rotation_deg(
        chopper["park_open_angle"], model.resolver_offset_deg, model.resolver_sign
    ) == pytest.approx(275.0)


def test_build_rotation_model_uses_documented_defaults_for_optional_metadata():
    chopper = _canonical()
    chopper.pop("positive_speed_rotation_direction")
    chopper.pop("resolver_positive_direction")
    chopper.pop("disk_delay")

    model = build_rotation_model(chopper)

    assert model.positive_speed_rotation_direction == CW
    assert model.resolver_sign == -1
    assert model.disk_delay_deg == pytest.approx(0.0)
    assert model.cw_disk_delay_deg == pytest.approx(0.0)
    assert model.ccw_disk_delay_deg == pytest.approx(0.0)


def test_direction_specific_disk_delays_override_default_disk_delay():
    chopper = _canonical(disk_delay=9.0, cw_disk_delay=5.3, ccw_disk_delay=6.6)
    model = build_rotation_model(chopper)

    assert disk_delay_for_rotation(
        CW, model.disk_delay_deg, model.cw_disk_delay_deg, model.ccw_disk_delay_deg
    ) == pytest.approx(5.3)
    assert disk_delay_for_rotation(
        CCW, model.disk_delay_deg, model.cw_disk_delay_deg, model.ccw_disk_delay_deg
    ) == pytest.approx(6.6)


@pytest.mark.parametrize(
    ("motor_position", "resolver_direction", "expected_sign"),
    [
        (UPSTREAM, CW, 1),
        (DOWNSTREAM, CW, -1),
    ],
)
def test_single_opening_parked_resolver_perturbation_follows_resolver_polarity(
    motor_position, resolver_direction, expected_sign
):
    chopper = _canonical(
        slit_edges=[[0.0, 80.0]],
        motor_position=motor_position,
        resolver_positive_direction=resolver_direction,
        park_open_angle=125.0,
    )
    model = build_rotation_model(chopper)

    centered = parked_rotation_deg(
        125.0, model.resolver_offset_deg, model.resolver_sign
    )
    perturbed = parked_rotation_deg(
        135.0, model.resolver_offset_deg, model.resolver_sign
    )

    assert centered == pytest.approx(40.0)
    assert model.resolver_sign == expected_sign
    assert wrap180(perturbed - centered) == pytest.approx(expected_sign * 10.0)


@pytest.mark.parametrize(
    ("positive_direction", "speed", "expected_delta"),
    [
        (CW, 14.0, 10.0),
        (CW, -14.0, -10.0),
    ],
)
def test_single_opening_phase_perturbation_follows_effective_spin(
    positive_direction, speed, expected_delta
):
    chopper = _canonical(positive_speed_rotation_direction=positive_direction)
    spin_sign = runtime_spin_sign(speed, positive_direction)
    effective_direction = CW if spin_sign >= 0 else CCW
    phase0 = compute_phase_center_delay_deg(
        60.0,
        30.0,
        DOWNSTREAM,
        effective_direction,
    )

    rot0 = _spinning(chopper, phase0, speed)
    rot1 = _spinning(chopper, phase0 + 10.0, speed)

    assert rot0 == pytest.approx(45.0)
    assert wrap180(rot1 - rot0) == pytest.approx(expected_delta)


@pytest.mark.parametrize(
    ("motor_position", "positive_direction", "speed"),
    [
        (UPSTREAM, CW, 14.0),
        (DOWNSTREAM, CW, 14.0),
    ],
)
def test_single_opening_phase_reference_centers_opening_for_motor_and_spin_combos(
    motor_position, positive_direction, speed
):
    chopper = _canonical(
        slit_edges=[[0.0, 70.0]],
        motor_position=motor_position,
        positive_speed_rotation_direction=positive_direction,
        tdc_resolver_position=20.0,
        park_open_angle=355.0,
        disk_delay=3.0,
    )
    phase = compute_phase_center_delay_deg(
        20.0,
        355.0,
        motor_position,
        positive_direction,
        disk_delay_deg=3.0,
    )

    assert _spinning(chopper, phase, speed) == pytest.approx(35.0)


def test_multi_opening_index_zero_can_derive_park_setpoints_for_every_window():
    chopper = _canonical(
        slit_edges=[[0.0, 20.0], [90.0, 120.0], [250.0, 310.0]],
        motor_position=UPSTREAM,
        resolver_positive_direction=CW,
        parked_opening_index=0,
        park_open_angle=180.0,
    )
    model = build_rotation_model(chopper)
    centers = [opening_center_deg(edges) for edges in chopper["slit_edges"]]
    expected_resolvers = [180.0, 275.0, 90.0]

    for resolver_angle, center in zip(expected_resolvers, centers):
        assert parked_rotation_deg(
            resolver_angle, model.resolver_offset_deg, model.resolver_sign
        ) == pytest.approx(center)


def test_multi_opening_nonzero_index_can_derive_phase_setpoints_for_every_window():
    chopper = _canonical(
        slit_edges=[[0.0, 20.0], [90.0, 110.0], [245.0, 275.0]],
        motor_position=DOWNSTREAM,
        positive_speed_rotation_direction=CW,
        parked_opening_index=1,
        tdc_resolver_position=20.0,
        park_open_angle=100.0,
        disk_delay=7.0,
    )
    centers = [opening_center_deg(edges) for edges in chopper["slit_edges"]]
    expected_phases = [197.0, 287.0, 87.0]

    for phase, center in zip(expected_phases, centers):
        assert _spinning(chopper, phase, speed=14.0) == pytest.approx(center)


def test_opening_center_and_width_handle_wraparound():
    opening = [350.0, 10.0]

    assert opening_width_deg(opening) == pytest.approx(20.0)
    assert opening_center_deg(opening) == pytest.approx(0.0)


def test_opening_center_and_width_handle_full_circle():
    opening = [0.0, 360.0]

    assert opening_width_deg(opening) == pytest.approx(360.0)
    assert opening_center_deg(opening) == pytest.approx(180.0)
