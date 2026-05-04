from copy import deepcopy

from nicos_ess.gui.widgets.chopper_math import wrap360

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
    "disk_rotation_direction": "CCW",
    "phase_tdc_center_window_delay": 90.0,
}

_FAKE_DISC_2 = {
    **_FAKE_DOUBLE_DISC_BASE,
    "chopper": FAKE_DISC_2_NAME,
    "motor_position": "downstream",
    "disk_rotation_direction": "CW",
    "phase_tdc_center_window_delay": -90.0,
}

_EXPECTED_OPENING_PHASES = {
    (FAKE_DISC_1_NAME, 1): {0: 90.0, 1: 180.0},
    (FAKE_DISC_1_NAME, -1): {0: 270.0, 1: 180.0},
    (FAKE_DISC_2_NAME, 1): {0: 270.0, 1: 180.0},
    (FAKE_DISC_2_NAME, -1): {0: 90.0, 1: 180.0},
}


def fake_double_disc_choppers() -> tuple[dict, dict]:
    return deepcopy(_FAKE_DISC_1), deepcopy(_FAKE_DISC_2)


def fake_expected_phase(
    chopper: dict | str, speed_hz: float, opening_index: int
) -> float:
    chopper_name = chopper["chopper"] if isinstance(chopper, dict) else chopper
    speed_sign = 1 if float(speed_hz) > 0.0 else -1
    return _EXPECTED_OPENING_PHASES[(chopper_name, speed_sign)][int(opening_index)]


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
