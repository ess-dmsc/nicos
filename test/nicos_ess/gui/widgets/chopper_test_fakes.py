from copy import deepcopy

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

DOWN_GUIDE_ANGLE_DEG = 270.0
FAKE_DISC_1_NAME = "fake_disc_1"
FAKE_DISC_2_NAME = "fake_disc_2"


_FAKE_DOUBLE_DISC_BASE = {
    "slit_edges": [[0.0, 40.0], [100.0, 120.0]],
    "parked_opening_index": 0,
    "park_edge_1": 160.0,
    "park_edge_2": 200.0,
    "park_open_angle": 180.0,
    "park_close_angle": 0.0,
    "tdc_resolver_position": 90.0,
}

_FAKE_DISC_1 = {
    **_FAKE_DOUBLE_DISC_BASE,
    "chopper": FAKE_DISC_1_NAME,
    "motor_position": "upstream",
    "positive_speed_rotation_direction": "CW",
    "resolver_positive_direction": "CW",
    "disk_delay": 0.0,
}

_FAKE_DISC_2 = {
    **_FAKE_DOUBLE_DISC_BASE,
    "chopper": FAKE_DISC_2_NAME,
    "motor_position": "downstream",
    "positive_speed_rotation_direction": "CW",
    "resolver_positive_direction": "CW",
    "disk_delay": 0.0,
}


def fake_double_disc_choppers() -> tuple[dict, dict]:
    return deepcopy(_FAKE_DISC_1), deepcopy(_FAKE_DISC_2)


def fake_expected_phase(
    chopper: dict | str, speed_hz: float, opening_index: int
) -> float:
    if not isinstance(chopper, dict):
        chopper = {
            FAKE_DISC_1_NAME: _FAKE_DISC_1,
            FAKE_DISC_2_NAME: _FAKE_DISC_2,
        }[chopper]
    model = build_rotation_model(chopper)
    opening_center = opening_center_deg(chopper["slit_edges"][int(opening_index)])
    spin_sign = runtime_phase_sign(
        speed_hz, model.positive_speed_rotation_direction
    )
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
    return wrap360(
        ref_phase - spin_sign * wrap180(opening_center - model.parked_opening_center_deg)
    )


def fake_opening_intervals_qt(
    chopper: dict, rotation_angle: float
) -> list[tuple[float, float]]:
    return [
        (wrap360(-float(end) + rotation_angle), wrap360(-float(start) + rotation_angle))
        for start, end in chopper["slit_edges"]
    ]


def fake_opening_intervals_for_base_rotation(
    chopper: dict, base_rotation: float, guide_angle: float = DOWN_GUIDE_ANGLE_DEG
) -> list[tuple[float, float]]:
    return fake_opening_intervals_qt(chopper, wrap360(base_rotation + guide_angle))


def fake_interval_contains(angle: float, interval: tuple[float, float]) -> bool:
    angle = wrap360(angle)
    start, end = interval
    if end < start:
        return angle >= start or angle <= end
    return start <= angle <= end
