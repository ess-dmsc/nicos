description = "NMX WLS-2 Chopper (double disc)"

pv_root_1 = "NMX-ChpSy1:Chop-WLS-201:"
pv_root_2 = "NMX-ChpSy1:Chop-WLS-202:"
chic_root = "NMX-ChpSy1:Chop-CHIC-001:"


def _normalize_angle(angle):
    """Normalize angle to [0, 360)."""
    return angle % 360.0


def calculate_spin_direction(hw_direction, mounting_direction):
    """
    Return the spin direction as seen from the beam (source -> sample).

    hw_direction: "CW"/"CCW" as seen from motor side.
    mounting_direction: "upstream" or "downstream".
    """
    hw_direction = hw_direction.upper()
    mounting_direction = mounting_direction.lower()

    if mounting_direction == "upstream":
        # Looking from the opposite side flips CW/CCW.
        if hw_direction == "CW":
            return "CCW"
        if hw_direction == "CCW":
            return "CW"
    elif mounting_direction == "downstream":
        # Same face as the motor drawing.
        if hw_direction in ("CW", "CCW"):
            return hw_direction

    raise ValueError(
        f"Unsupported direction/mounting combination: "
        f"direction={hw_direction!r}, mounting={mounting_direction!r}"
    )


def _spin_sign(spin_direction):
    """
    Internal helper: map spin_direction -> sign.

    We choose:
      spin_direction == "CW"   -> sign = -1
      spin_direction == "CCW"  -> sign = +1

    This makes "positive phase" always move the window opposite
    to the physical rotation direction in the GUI.
    """
    if spin_direction.upper() == "CW":
        return -1.0
    if spin_direction.upper() == "CCW":
        return 1.0
    raise ValueError(f"Unknown spin direction: {spin_direction!r}")


def calculate_resolver_offset(park_open_angle, disc_opening, spin_direction):
    """
    Choose resolver_offset so that when the disc is parked at `park_open_angle`,
    the *center* of the park window lies exactly on the beam guide line.

    All angles are in the engineering coordinate system (motor angles),
    but spin_direction encodes how the disc is seen from the beam side.
    """
    slit_center = disc_opening / 2.0  # one opening [0, disc_opening] -> center
    sign = _spin_sign(spin_direction)
    # Condition: center_gui(park) == guide_angle
    # -> resolver_offset = slit_center + sign * park_open_angle
    return _normalize_angle(slit_center + sign * park_open_angle)


def calculate_tdc_offset(center_window_delay, disc_opening, spin_direction):
    """
    Choose tdc_offset so that when the chopper *phase* is set to
    `center_window_delay` (in degrees), the center of the park window
    lies exactly on the beam guide line while spinning.

    This is exactly your requirement:
      "if we set the phase to wls2b_hw_center_window_delay, then the center
       of the park window should be exactly at the beam guide line."
    """
    slit_center = disc_opening / 2.0
    sign = _spin_sign(spin_direction)
    # Condition at phase = center_window_delay:
    #   center_gui(phase=center_window_delay) == guide_angle
    # -> tdc_offset = slit_center - sign * center_window_delay
    return _normalize_angle(slit_center - sign * center_window_delay)


wls2a_hw_direction = "CW"
wls2a_hw_mounting_direction = "upstream"  # upstream should not flip visuals
wls2a_hw_disc_opening = 170.0
wls2a_hw_park_open_angle = 73.0
wls2a_hw_tdc_angle = 341.7
wls2a_hw_center_window_delay = 91.3

wls2b_hw_direction = "CW"
wls2b_hw_mounting_direction = "downstream"  # downstream should flip visuals
wls2b_hw_disc_opening = 170.0
wls2b_hw_park_open_angle = 165.0
wls2b_hw_tdc_angle = 342.5
wls2b_hw_center_window_delay = 177.5

# Spin directions as seen from the beam (source -> sample).
wls2a_spin_direction = calculate_spin_direction(
    wls2a_hw_direction,
    wls2a_hw_mounting_direction,
)
wls2b_spin_direction = calculate_spin_direction(
    wls2b_hw_direction,
    wls2b_hw_mounting_direction,
)


devices = dict(
    wls2a_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(pv_root_1),
        visibility=(),
    ),
    wls2a_chopper_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv="{}C_Execute".format(pv_root_1),
        writepv="{}C_Execute".format(pv_root_1),
        requires={"level": "admin"},
        visibility=(),
    ),
    wls2a_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The current speed.",
        readpv="{}Spd_R".format(pv_root_1),
        writepv="{}Spd_S".format(pv_root_1),
        precision=0.1,
        mapping={"0 Hz": 0, "14 Hz": 14},
    ),
    wls2a_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(pv_root_1),
        writepv="{}ChopDly-S".format(pv_root_1),
        abslimits=(0.0, 0.0),
    ),
    wls2a_chopper_phase=device(
        "nicos_ess.devices.transformer_devices.ChopperPhase",
        description="The phase of the chopper.",
        phase_ns_dev="wls2a_chopper_delay",
        mapped_speed_dev="wls2a_chopper_speed",
        offset=0,
        unit="degrees",
    ),
    wls2a_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(pv_root_1),
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    wls2a_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(pv_root_1),
    ),
    wls2a_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(pv_root_1),
        writepv="{}Park_S".format(pv_root_1),
        visibility=(),
    ),
    wls2a_chopper_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the WLS-2A chopper.",
        readpv="{}ParkPos_S".format(pv_root_1),
        writepv="{}ParkPos_S".format(pv_root_1),
    ),
    wls2a_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv="{}ConnectedR".format(chic_root),
        visibility=(),
        pva=True,
    ),
    wls2a_chopper_alarms=device(
        "nicos_ess.devices.epics.chopper.ChopperAlarms",
        description="The chopper alarms",
        pv_root=pv_root_1,
        visibility=(),
    ),
    wls2a_chopper=device(
        "nicos_ess.devices.epics.chopper.EssChopperController",
        description="The chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="wls2a_chopper_status",
        command="wls2a_chopper_control",
        speed="wls2a_chopper_speed",
        chic_conn="wls2a_chopper_chic",
        alarms="wls2a_chopper_alarms",
        slit_edges=[[0, 170]],
        resolver_offset=calculate_resolver_offset(
            wls2a_hw_park_open_angle,
            wls2a_hw_disc_opening,
            wls2a_spin_direction,
        ),
        tdc_offset=calculate_tdc_offset(
            wls2a_hw_center_window_delay,
            wls2a_hw_disc_opening,
            wls2a_spin_direction,
        ),
        spin_direction=wls2a_spin_direction,
        mounting_direction=wls2a_hw_mounting_direction,
    ),
    wls2b_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(pv_root_2),
        visibility=(),
    ),
    wls2b_chopper_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv="{}C_Execute".format(pv_root_2),
        writepv="{}C_Execute".format(pv_root_2),
        requires={"level": "admin"},
        visibility=(),
    ),
    wls2b_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The current speed.",
        readpv="{}Spd_R".format(pv_root_2),
        writepv="{}Spd_S".format(pv_root_2),
        precision=0.1,
        mapping={"0 Hz": 0, "14 Hz": 14},
    ),
    wls2b_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(pv_root_2),
        writepv="{}ChopDly-S".format(pv_root_2),
        abslimits=(0.0, 0.0),
    ),
    wls2b_chopper_phase=device(
        "nicos_ess.devices.transformer_devices.ChopperPhase",
        description="The phase of the chopper.",
        phase_ns_dev="wls2b_chopper_delay",
        mapped_speed_dev="wls2b_chopper_speed",
        offset=0,
        unit="degrees",
    ),
    wls2b_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(pv_root_2),
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    wls2b_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(pv_root_2),
    ),
    wls2b_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(pv_root_2),
        writepv="{}Park_S".format(pv_root_2),
        visibility=(),
    ),
    wls2b_chopper_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the WLS-2B chopper.",
        readpv="{}ParkPos_S".format(pv_root_2),
        writepv="{}ParkPos_S".format(pv_root_2),
    ),
    wls2b_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv="{}ConnectedR".format(chic_root),
        visibility=(),
    ),
    wls2b_chopper_alarms=device(
        "nicos_ess.devices.epics.chopper.ChopperAlarms",
        description="The chopper alarms",
        pv_root=pv_root_2,
        visibility=(),
    ),
    wls2b_chopper=device(
        "nicos_ess.devices.epics.chopper.EssChopperController",
        description="The chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="wls2b_chopper_status",
        command="wls2b_chopper_control",
        speed="wls2b_chopper_speed",
        chic_conn="wls2b_chopper_chic",
        alarms="wls2b_chopper_alarms",
        slit_edges=[[0, 170]],
        resolver_offset=calculate_resolver_offset(
            wls2b_hw_park_open_angle,
            wls2b_hw_disc_opening,
            wls2b_spin_direction,
        ),
        tdc_offset=calculate_tdc_offset(
            wls2b_hw_center_window_delay,
            wls2b_hw_disc_opening,
            wls2b_spin_direction,
        ),
        spin_direction=wls2b_spin_direction,
        mounting_direction=wls2b_hw_mounting_direction,
    ),
)
