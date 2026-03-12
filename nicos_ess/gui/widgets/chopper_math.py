import math
from dataclasses import dataclass
from typing import Optional

CW = "CW"
CCW = "CCW"
UPSTREAM = "upstream"
DOWNSTREAM = "downstream"

_CANONICAL_REQUIRED_KEYS = (
    "motor_position",
    "disk_rotation_direction",
    "parked_opening_index",
    "tdc_resolver_position",
    "park_open_angle",
    "phase_tdc_center_window_delay",
    "slit_edges",
)


def wrap360(value: float) -> float:
    return (value % 360.0 + 360.0) % 360.0


def wrap180(value: float) -> float:
    value = wrap360(value)
    if value > 180.0:
        value -= 360.0
    return value


def normalize_spin_direction(direction: str) -> str:
    normalized = str(direction).upper()
    if normalized not in (CW, CCW):
        raise ValueError(f"Invalid rotation direction: {direction!r}")
    return normalized


def normalize_motor_position(position: str) -> str:
    normalized = str(position).strip().lower()
    if normalized not in (UPSTREAM, DOWNSTREAM):
        raise ValueError(f"Invalid motor position: {position!r}")
    return normalized


def direction_to_sign(direction: str) -> int:
    return 1 if normalize_spin_direction(direction) == CW else -1


def apply_motor_side_transform(direction: str, motor_position: str) -> str:
    direction = normalize_spin_direction(direction)
    motor_position = normalize_motor_position(motor_position)
    if motor_position == UPSTREAM:
        return direction
    return CCW if direction == CW else CW


def opening_width_deg(opening: list[float]) -> float:
    start, end = opening
    return wrap360(float(end) - float(start))


def opening_center_deg(opening: list[float]) -> float:
    start, _ = opening
    return wrap360(float(start) + opening_width_deg(opening) / 2.0)


def center_from_edges(park_edge_1: float, park_edge_2: float) -> float:
    return opening_center_deg([park_edge_1, park_edge_2])


@dataclass(frozen=True)
class ChopperRotationModel:
    base_spin_direction: str
    phase_reference_sign: int
    parked_opening_index: int
    parked_opening_center_deg: float
    parked_opening_width_deg: float
    resolver_offset_deg: float
    spin_offset_deg: float
    expected_phase_delay_deg: float
    phase_delay_error_deg: float


def has_canonical_inputs(chopper: dict) -> bool:
    return all(chopper.get(key) is not None for key in _CANONICAL_REQUIRED_KEYS)


def build_rotation_model(chopper: dict, tol_deg: float = 1e-6) -> ChopperRotationModel:
    slit_edges = chopper["slit_edges"]
    if not slit_edges:
        raise ValueError("Canonical chopper model requires non-empty slit_edges")

    parked_opening_index = int(chopper["parked_opening_index"])
    if parked_opening_index < 0 or parked_opening_index >= len(slit_edges):
        raise ValueError(
            "parked_opening_index must reference an existing slit opening "
            f"(got {parked_opening_index}, total openings={len(slit_edges)})"
        )

    slit_start = wrap360(float(slit_edges[0][0]))
    if min(slit_start, 360.0 - slit_start) > tol_deg:
        raise ValueError(
            f"slit_edges must start at 0 degrees (got {slit_edges[0][0]!r})"
        )
    parked_opening = slit_edges[parked_opening_index]
    opening_center = opening_center_deg(parked_opening)
    opening_width = opening_width_deg(parked_opening)

    park_open_angle = float(chopper["park_open_angle"])
    tdc_resolver_position = float(chopper["tdc_resolver_position"])
    phase_delay = float(chopper["phase_tdc_center_window_delay"])

    park_edge_1 = chopper.get("park_edge_1")
    park_edge_2 = chopper.get("park_edge_2")
    if park_edge_1 is not None and park_edge_2 is not None:
        park_center = center_from_edges(float(park_edge_1), float(park_edge_2))
        park_width = opening_width_deg([float(park_edge_1), float(park_edge_2)])
        if abs(wrap180(park_center - park_open_angle)) > tol_deg:
            raise ValueError(
                "park_open_angle is inconsistent with park_edge_1/park_edge_2 "
                f"(center={park_center}, park_open={park_open_angle})"
            )
        if abs(wrap180(park_width - opening_width)) > tol_deg:
            raise ValueError(
                "Parked opening width does not match slit_edges at parked_opening_index "
                f"(park_width={park_width}, slit_width={opening_width})"
            )

    motor_position = normalize_motor_position(chopper["motor_position"])
    phase_delay_sign = 1 if motor_position == DOWNSTREAM else -1
    expected_phase_delay = wrap180(
        phase_delay_sign * (tdc_resolver_position - park_open_angle)
    )

    base_spin_direction = apply_motor_side_transform(
        chopper["disk_rotation_direction"], chopper["motor_position"]
    )
    base_sign = direction_to_sign(base_spin_direction)
    # Runtime phase-motion sign is defined opposite to the legacy
    # motor-side phase-delay sign so configured phase references align
    # opening centers with the beam guide for both single/multi-opening discs.
    phase_reference_sign = -phase_delay_sign
    phase_sign = base_sign * phase_reference_sign

    resolver_sign = -phase_sign
    # Parked reference: when resolver == park_open_angle, parked opening center
    # aligns with the beam guide in widget space.
    resolver_offset = wrap180(opening_center - resolver_sign * park_open_angle)
    # Spinning reference: when phase equals phase_tdc_center_window_delay (for
    # nominal spin direction), parked opening center aligns with beam guide.
    spin_offset = wrap180(opening_center + phase_delay * phase_sign)

    return ChopperRotationModel(
        base_spin_direction=base_spin_direction,
        phase_reference_sign=phase_reference_sign,
        parked_opening_index=parked_opening_index,
        parked_opening_center_deg=opening_center,
        parked_opening_width_deg=opening_width,
        resolver_offset_deg=resolver_offset,
        spin_offset_deg=spin_offset,
        expected_phase_delay_deg=expected_phase_delay,
        phase_delay_error_deg=wrap180(phase_delay - expected_phase_delay),
    )


def runtime_spin_sign(speed_hz: Optional[float], base_spin_direction: str) -> int:
    base_sign = direction_to_sign(base_spin_direction)
    if speed_hz is None:
        return base_sign
    speed_hz = float(speed_hz)
    if speed_hz > 0:
        return base_sign
    if speed_hz < 0:
        return -base_sign
    return base_sign


def runtime_phase_sign(
    speed_hz: Optional[float], base_spin_direction: str, phase_reference_sign: int
) -> int:
    return runtime_spin_sign(speed_hz, base_spin_direction) * int(phase_reference_sign)


def parked_rotation_deg(
    resolver_angle_deg: float,
    resolver_offset_deg: float,
    base_spin_direction: str,
    phase_reference_sign: int = 1,
) -> float:
    resolver_sign = -direction_to_sign(base_spin_direction) * int(phase_reference_sign)
    return wrap360(
        resolver_sign * float(resolver_angle_deg) + float(resolver_offset_deg)
    )


def spinning_rotation_deg(
    phase_angle_deg: float,
    speed_hz: Optional[float],
    spin_offset_deg: float,
    base_spin_direction: str,
    phase_reference_sign: int = 1,
) -> float:
    # Positive phase shift moves opposite to the actual spin direction.
    spin_sign = runtime_phase_sign(speed_hz, base_spin_direction, phase_reference_sign)
    phase_contribution = -spin_sign * float(phase_angle_deg)
    return wrap360(phase_contribution + float(spin_offset_deg))
