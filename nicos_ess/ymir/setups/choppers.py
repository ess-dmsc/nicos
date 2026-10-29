description = "The mini-chopper for YMIR"

pv_root = "YMIR-ChpSy1:Chop-MIC-101:"
chic_root = "YMIR-ChpSy1:Chop-CHIC-001:"

devices = dict(
    mini_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv=f"{pv_root}ChopState_R",
        visibility=(),
    ),
    mini_chopper_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv=f"{pv_root}C_ExecuteUser",
        writepv=f"{pv_root}C_ExecuteUser",
        requires={"level": "admin"},
        visibility=(),
    ),
    mini_chopper_speed=device(
        "nicos_ess.devices.epics.chopper.EssChopperSpeed",
        description="The current speed.",
        readpv=f"{pv_root}Spd_R",
        writepv=f"{pv_root}Spd_S",
        precision=0.1,
        mapping={"-14": -14, "-7": -7, "0": 0, "7": 7, "14": 14},
        in_phase="mini_chopper_phased",
        state="mini_chopper_status",
    ),
    mini_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv=f"{pv_root}ChopDly-S",
        writepv=f"{pv_root}ChopDly-S",
    ),
    mini_chopper_total_delay=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=(
            "The total delay (MechDly-S + BeamPosDly-S + ChopDly-S). "
            "The full delay that is applied on proton on target event for "
            "the driving signal of the chopper."
        ),
        readpv=f"{pv_root}TotDly",
        visibility=("metadata", "namespace"),
    ),
    mini_chopper_phase=device(
        "nicos_ess.devices.transformer_devices.ChopperPhase",
        description="The phase of the chopper.",
        phase_ns_dev="mini_chopper_delay",
        mapped_speed_dev="mini_chopper_speed",
        offset=0,
        unit="degrees",
    ),
    mini_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv=f"{pv_root}DiffTSSamples",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    mini_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv=f"{pv_root}InPhaseTS-R",
    ),
    mini_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Park angle: rotor position (Pos_R), park setpoint (Park_S).",
        readpv=f"{pv_root}Pos_R",
        writepv=f"{pv_root}Park_S",
        precision=0.5,
        visibility=(),
    ),
    mini_chopper_park_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The park status for the chopper.",
        readpv=f"{pv_root}ParkStatus_R",
    ),
    mini_chopper_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the chopper.",
        readpv=f"{pv_root}C_Park",
        writepv=f"{pv_root}C_Park",
    ),
    mini_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv=f"{chic_root}ConnectedR",
        visibility=(),
        pva=True,
    ),
    mini_chopper_alarms=device(
        "nicos_ess.devices.epics.chopper.NewChopperAlarms",
        description="The chopper alarms",
        pv_root=pv_root,
        visibility=(),
    ),
    mini_chopper=device(
        "nicos_ess.devices.epics.chopper.NewEssChopperController",
        description="The chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="mini_chopper_status",
        command="mini_chopper_control",
        speed="mini_chopper_speed",
        total_delay="mini_chopper_total_delay",
        park_angle="mini_chopper_park_angle",
        delay_errors="mini_chopper_delay_errors",
        chic_conn="mini_chopper_chic",
        alarms="mini_chopper_alarms",
        # Placeholder geometry: the disc is not documented yet.
        slit_edges=[[0.0, 90.0]],
        beam_position=0.0,
        legacy_spd_sign=True,
    ),
)
