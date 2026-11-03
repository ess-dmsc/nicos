description = "NMX WLS-2 Chopper disc 1 (double disc)"

pv_root_1 = "NMX-ChpSy1:Chop-WLS-201:"
chic_root = "NMX-ChpSy1:Chop-CHIC-001:"

devices = dict(
    wls2a_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv=f"{pv_root_1}ChopState_R",
        visibility=(),
    ),
    wls2a_chopper_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv=f"{pv_root_1}C_Execute",
        writepv=f"{pv_root_1}C_Execute",
        requires={"level": "admin"},
        visibility=(),
    ),
    wls2a_chopper_speed=device(
        "nicos_ess.devices.epics.chopper.EssChopperSpeed",
        description="The current speed.",
        readpv=f"{pv_root_1}Spd_R",
        writepv=f"{pv_root_1}Spd_S",
        precision=0.1,
        mapping={"0": 0, "14": 14},
        in_phase="wls2a_chopper_phased",
        state="wls2a_chopper_status",
    ),
    wls2a_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv=f"{pv_root_1}ChopDly-S",
        writepv=f"{pv_root_1}ChopDly-S",
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
        readpv=f"{pv_root_1}DiffTSSamples",
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    wls2a_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv=f"{pv_root_1}InPhaseTS-R",
    ),
    wls2a_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Park angle: rotor position (Pos_R), park setpoint (Park_S).",
        readpv=f"{pv_root_1}Pos_R",
        writepv=f"{pv_root_1}Park_S",
        precision=0.5,
        visibility=(),
    ),
    wls2a_chopper_park_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The park status for the WLS-2A chopper.",
        readpv=f"{pv_root_1}ParkStatus_R",
    ),
    wls2a_chopper_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the WLS-2A chopper.",
        readpv=f"{pv_root_1}C_Park",
        writepv=f"{pv_root_1}C_Park",
    ),
    wls2a_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv=f"{chic_root}ConnectedR",
        visibility=(),
        pva=True,
    ),
    wls2a_chopper_alarms=device(
        "nicos_ess.devices.epics.chopper.NewChopperAlarms",
        description="The chopper alarms",
        pv_root=pv_root_1,
        visibility=(),
    ),
    wls2a_chopper_total_delay=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=(
            "The total delay (MechDly-S + BeamPosDly-S + ChopDly-S). "
            "The full delay that is applied on proton on target event for "
            "the driving signal of the chopper."
        ),
        readpv=f"{pv_root_1}TotDly",
        visibility=("metadata", "namespace"),
    ),
    wls2a_chopper=device(
        "nicos_ess.devices.epics.chopper.NewEssChopperController",
        description="The chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="wls2a_chopper_status",
        command="wls2a_chopper_control",
        speed="wls2a_chopper_speed",
        chic_conn="wls2a_chopper_chic",
        alarms="wls2a_chopper_alarms",
        total_delay="wls2a_chopper_total_delay",
        park_angle="wls2a_chopper_park_angle",
        delay_errors="wls2a_chopper_delay_errors",
        slit_edges=[[0.0, 170.0]],
        beam_position=176.0,
        resolver_sign=-1,
        tdc_resolver_position=342.0,
        distance=50.255,
        legacy_spd_sign=True,
    ),
)
