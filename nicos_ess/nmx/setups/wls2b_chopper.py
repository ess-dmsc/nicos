description = "NMX WLS-2 Chopper disc 2 (double disc)"

pv_root_2 = "NMX-ChpSy1:Chop-WLS-202:"
chic_root = "NMX-ChpSy1:Chop-CHIC-001:"

devices = dict(
    wls2b_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv=f"{pv_root_2}ChopState_R",
        visibility=(),
    ),
    wls2b_chopper_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv=f"{pv_root_2}C_Execute",
        writepv=f"{pv_root_2}C_Execute",
        requires={"level": "admin"},
        visibility=(),
    ),
    wls2b_chopper_speed=device(
        "nicos_ess.devices.epics.chopper.EssChopperSpeed",
        description="The current speed.",
        readpv=f"{pv_root_2}Spd_R",
        writepv=f"{pv_root_2}Spd_S",
        precision=0.1,
        mapping={"0": 0, "14": 14},
        in_phase="wls2b_chopper_phased",
        state="wls2b_chopper_status",
    ),
    wls2b_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv=f"{pv_root_2}ChopDly-S",
        writepv=f"{pv_root_2}ChopDly-S",
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
        readpv=f"{pv_root_2}DiffTSSamples",
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    wls2b_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv=f"{pv_root_2}InPhaseTS-R",
    ),
    wls2b_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Park angle: rotor position (Pos_R), park setpoint (Park_S).",
        readpv=f"{pv_root_2}Pos_R",
        writepv=f"{pv_root_2}Park_S",
        precision=0.5,
        visibility=(),
    ),
    wls2b_chopper_park_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The park status for the WLS-2B chopper.",
        readpv=f"{pv_root_2}ParkStatus_R",
    ),
    wls2b_chopper_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the WLS-2B chopper.",
        readpv=f"{pv_root_2}C_Park",
        writepv=f"{pv_root_2}C_Park",
    ),
    wls2b_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv=f"{chic_root}ConnectedR",
        visibility=(),
    ),
    wls2b_chopper_alarms=device(
        "nicos_ess.devices.epics.chopper.NewChopperAlarms",
        description="The chopper alarms",
        pv_root=pv_root_2,
        visibility=(),
    ),
    wls2b_chopper_total_delay=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=(
            "The total delay (MechDly-S + BeamPosDly-S + ChopDly-S). "
            "The full delay that is applied on proton on target event for "
            "the driving signal of the chopper."
        ),
        readpv=f"{pv_root_2}TotDly",
        visibility=("metadata", "namespace"),
    ),
    wls2b_chopper=device(
        "nicos_ess.devices.epics.chopper.NewEssChopperController",
        description="The chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="wls2b_chopper_status",
        command="wls2b_chopper_control",
        speed="wls2b_chopper_speed",
        chic_conn="wls2b_chopper_chic",
        alarms="wls2b_chopper_alarms",
        total_delay="wls2b_chopper_total_delay",
        park_angle="wls2b_chopper_park_angle",
        delay_errors="wls2b_chopper_delay_errors",
        slit_edges=[[0.0, 170.0]],
        beam_position=261.0,
        resolver_sign=1,
        tdc_resolver_position=342.0,
        distance=50.355,
        legacy_spd_sign=True,
    ),
)
