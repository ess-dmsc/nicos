"""Where a chopper disc is drawn, from its NeXus geometry and its readbacks.

The chopper widget shows each disc seen from the moderator looking towards the
sample, and describes it exactly like the NeXus file (NXdisk_chopper) does:

* ``slit_edges``: the openings, in degrees anticlockwise seen from the moderator,
  counted from the disc's TDC mark;
* ``beam_position``: the angle from the TDC sensor to the beam, same sense.

A parked disc is placed from its resolver reading, which needs two more numbers:

* ``tdc_resolver_position``: the reading at which the TDC mark is at the sensor;
* ``resolver_sign``: +1 if the reading rises while the disc turns clockwise seen
  from the moderator (positive Spd_R), -1 if it falls.

The disc's angle ``a`` is drawn at screen angle ``rotation + a`` (Qt: degrees
anticlockwise from 3 o'clock), where ``rotation`` is where the TDC mark is drawn.
The beam is at the guide angle ``g``, so the sensor is at ``g - beam_position``.

Parked at reading ``r``, the mark is ``resolver_sign * (r - tdc)`` clockwise of the
sensor. A disc without resolver values is drawn parked with the mark at the sensor.
Spinning, the mark passes the sensor TotDly after T0; at T0 it is
``phase = 360 * |f| * TotDly`` degrees short of the sensor, against its direction
of travel. Positive Spd_R turns clockwise seen from the moderator (chopper group
convention); the NeXus sign SpdNexus-R = -Spd_R.
"""

GUIDE_ANGLES = {"RIGHT": 0.0, "UP": 90.0, "LEFT": 180.0, "DOWN": 270.0}


def wrap360(value: float) -> float:
    return float(value) % 360.0


def is_chopper_moving(speed_hz) -> bool:
    return speed_hz is not None and abs(float(speed_hz)) >= 2.0


def phase_deg(total_delay_ns: float, speed_hz: float) -> float:
    """TotDly as rotation of the disc: 360 * |f| * TotDly."""
    return float(total_delay_ns) * abs(float(speed_hz)) * 360.0 / 1e9


def check_geometry(chopper: dict) -> None:
    """Raise ValueError if the disc cannot be drawn at all."""
    edges = chopper.get("slit_edges")
    if not edges or any(len(opening) != 2 for opening in edges):
        raise ValueError("slit_edges must be a non-empty list of [start, end]")
    if chopper.get("beam_position") is None:
        raise ValueError("beam_position is not set")
    if str(chopper.get("guide_position", "DOWN")).upper() not in GUIDE_ANGLES:
        raise ValueError(f"invalid guide_position {chopper['guide_position']!r}")


def guide_angle(chopper: dict) -> float:
    return GUIDE_ANGLES[str(chopper.get("guide_position", "DOWN")).upper()]


def clockwise(chopper: dict, speed_hz: float) -> bool:
    """True if the disc turns clockwise seen from the moderator."""
    spd_r = speed_hz if chopper.get("legacy_spd_sign") else -speed_hz
    return spd_r > 0


def parked_rotation_deg(chopper: dict, resolver_deg: float | None) -> float:
    sensor = guide_angle(chopper) - float(chopper["beam_position"])
    if (
        resolver_deg is None
        or chopper.get("resolver_sign") is None
        or chopper.get("tdc_resolver_position") is None
    ):
        return wrap360(sensor)
    turned = chopper["resolver_sign"] * (
        float(resolver_deg) - float(chopper["tdc_resolver_position"])
    )
    return wrap360(sensor - turned)


def spinning_rotation_deg(chopper: dict, phase_deg: float, speed_hz: float) -> float:
    sensor = guide_angle(chopper) - float(chopper["beam_position"])
    behind = float(phase_deg) if clockwise(chopper, speed_hz) else -float(phase_deg)
    return wrap360(sensor + behind)
