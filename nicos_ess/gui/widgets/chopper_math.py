from dataclasses import dataclass
from typing import Optional

CW = "CW"
CCW = "CCW"
UPSTREAM = "upstream"
DOWNSTREAM = "downstream"

_CANONICAL_REQUIRED_KEYS = (
    "slit_edges",
    "motor_position",
    "parked_opening_index",
    "tdc_resolver_position",
    "park_open_angle",
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
    motor_position: str
    positive_speed_rotation_direction: str
    resolver_positive_direction: str
    resolver_sign: int
    parked_opening_index: int
    parked_opening_center_deg: float
    parked_opening_width_deg: float
    tdc_resolver_position_deg: float
    park_open_angle_deg: float
    resolver_offset_deg: float
    phase_tdc_center_window_delay_deg: float
    disk_delay_deg: float
    disk_delay_cw_deg: float
    disk_delay_ccw_deg: float


def has_canonical_inputs(chopper: dict) -> bool:
    return all(
        chopper.get(key) is not None for key in _CANONICAL_REQUIRED_KEYS
    ) and bool(chopper.get("slit_edges"))


def resolver_direction_sign(direction: str, motor_position: str) -> int:
    """Map resolver CW/CCW polarity to the widget's drawing coordinate.

    Resolver angle polarity is a property of the resolver/disk coordinate frame,
    not of the current spin direction. Looking at opposite motor sides reverses
    the visual drawing coordinate, so downstream-mounted motors get the opposite
    sign from upstream-mounted motors for the same resolver polarity.
    """
    motor_sign = 1 if normalize_motor_position(motor_position) == UPSTREAM else -1
    return direction_to_sign(direction) * motor_sign


def compute_phase_center_delay_deg(
    tdc_resolver_position: float,
    park_open_angle: float,
    motor_position: str,
    effective_rotation_direction: str,
    disk_delay_deg: float = 0.0,
) -> float:
    """Return the phase/delay angle that centers the parked opening.

    Markus' CW/CCW input is the effective runtime rotation direction. The PLC
    positive-speed convention is mapped to this before calling the formula.
    """
    motor_position = normalize_motor_position(motor_position)
    rotation_direction = normalize_spin_direction(effective_rotation_direction)
    tdc = float(tdc_resolver_position)
    park = float(park_open_angle)
    offset = float(disk_delay_deg)

    if (
        motor_position == UPSTREAM
        and rotation_direction == CW
        or motor_position == DOWNSTREAM
        and rotation_direction == CCW
    ):
        delay = 360.0 - tdc + park
    elif (
        motor_position == DOWNSTREAM
        and rotation_direction == CW
        or motor_position == UPSTREAM
        and rotation_direction == CCW
    ):
        delay = tdc - park
    else:
        raise ValueError(
            "Invalid motor position / effective rotation direction "
            f"combination: {motor_position!r}, {rotation_direction!r}"
        )
    return wrap360(delay + offset)


def sign_to_direction(sign: int) -> str:
    return CW if int(sign) >= 0 else CCW


def disk_delay_for_direction(
    direction: str,
    disk_delay_deg: float = 0.0,
    disk_delay_cw_deg: Optional[float] = None,
    disk_delay_ccw_deg: Optional[float] = None,
) -> float:
    fallback = float(disk_delay_deg)
    if normalize_spin_direction(direction) == CW:
        return fallback if disk_delay_cw_deg is None else float(disk_delay_cw_deg)
    return fallback if disk_delay_ccw_deg is None else float(disk_delay_ccw_deg)


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
    disk_delay = float(chopper.get("disk_delay", 0.0))
    disk_delay_cw = disk_delay_for_direction(
        CW,
        disk_delay,
        chopper.get("disk_delay_cw"),
        chopper.get("disk_delay_ccw"),
    )
    disk_delay_ccw = disk_delay_for_direction(
        CCW,
        disk_delay,
        chopper.get("disk_delay_cw"),
        chopper.get("disk_delay_ccw"),
    )

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
    positive_speed_direction = normalize_spin_direction(
        chopper.get("positive_speed_rotation_direction", CW)
    )
    resolver_direction = normalize_spin_direction(
        chopper.get("resolver_positive_direction", CW)
    )
    resolver_sign = resolver_direction_sign(resolver_direction, motor_position)
    positive_speed_disk_delay = disk_delay_for_direction(
        positive_speed_direction, disk_delay, disk_delay_cw, disk_delay_ccw
    )
    phase_center_delay = compute_phase_center_delay_deg(
        tdc_resolver_position,
        park_open_angle,
        motor_position,
        positive_speed_direction,
        positive_speed_disk_delay,
    )
    # Parked reference: when resolver == park_open_angle, parked opening center
    # aligns with the beam guide in widget space.
    resolver_offset = wrap180(opening_center - resolver_sign * park_open_angle)

    return ChopperRotationModel(
        motor_position=motor_position,
        positive_speed_rotation_direction=positive_speed_direction,
        resolver_positive_direction=resolver_direction,
        resolver_sign=resolver_sign,
        parked_opening_index=parked_opening_index,
        parked_opening_center_deg=opening_center,
        parked_opening_width_deg=opening_width,
        tdc_resolver_position_deg=tdc_resolver_position,
        park_open_angle_deg=park_open_angle,
        resolver_offset_deg=resolver_offset,
        phase_tdc_center_window_delay_deg=phase_center_delay,
        disk_delay_deg=disk_delay,
        disk_delay_cw_deg=disk_delay_cw,
        disk_delay_ccw_deg=disk_delay_ccw,
    )


def runtime_spin_sign(
    speed_hz: Optional[float], positive_speed_rotation_direction: str
) -> int:
    base_sign = direction_to_sign(positive_speed_rotation_direction)
    if speed_hz is None:
        return base_sign
    speed_hz = float(speed_hz)
    if speed_hz > 0:
        return base_sign
    if speed_hz < 0:
        return -base_sign
    return base_sign


def runtime_phase_sign(
    speed_hz: Optional[float], positive_speed_rotation_direction: str
) -> int:
    return runtime_spin_sign(speed_hz, positive_speed_rotation_direction)


def parked_rotation_deg(
    resolver_angle_deg: float,
    resolver_offset_deg: float,
    resolver_sign: int,
) -> float:
    return wrap360(
        resolver_sign * float(resolver_angle_deg) + float(resolver_offset_deg)
    )


def spinning_rotation_deg(
    phase_angle_deg: float,
    speed_hz: Optional[float],
    parked_opening_center_deg: float,
    tdc_resolver_position_deg: float,
    park_open_angle_deg: float,
    motor_position: str,
    positive_speed_rotation_direction: str,
    disk_delay_deg: float = 0.0,
    disk_delay_cw_deg: Optional[float] = None,
    disk_delay_ccw_deg: Optional[float] = None,
) -> float:
    # Markus' CW/CCW formula is based on effective runtime direction: for a PLC
    # convention where positive speed is CW, negative speed is effective CCW.
    spin_sign = runtime_phase_sign(speed_hz, positive_speed_rotation_direction)
    effective_direction = sign_to_direction(spin_sign)
    effective_disk_delay = disk_delay_for_direction(
        effective_direction, disk_delay_deg, disk_delay_cw_deg, disk_delay_ccw_deg
    )
    phase_reference = compute_phase_center_delay_deg(
        tdc_resolver_position_deg,
        park_open_angle_deg,
        motor_position,
        effective_direction,
        effective_disk_delay,
    )
    return wrap360(
        float(parked_opening_center_deg)
        - spin_sign * wrap180(float(phase_angle_deg) - phase_reference)
    )
