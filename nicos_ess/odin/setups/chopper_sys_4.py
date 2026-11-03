description = "The choppers in chopper system 4 for ODIN"

foc5_pv_root = "ODIN-ChpSy4:Chop-FOC-501:"
vacuum_pv_root = "ODIN-VacInstr:Vac-VGP-"
chpsy4_chic_pv_root = "ODIN-ChpSy4:Chop-CHIC-001:"


devices = dict(
    chpsy4_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv=f"{chpsy4_chic_pv_root}ConnectedR",
        visibility=(),
        pva=True,
    ),
    foc5_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv=f"{foc5_pv_root}ChopState_R",
        visibility=(),
    ),
    foc5_chopper_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv=f"{foc5_pv_root}C_ExecuteUser",
        writepv=f"{foc5_pv_root}C_ExecuteUser",
        requires={"level": "admin"},
        visibility=(),
    ),
    foc5_chopper_speed=device(
        "nicos_ess.devices.epics.chopper.EssChopperSpeed",
        description="The current speed.",
        readpv=f"{foc5_pv_root}Spd_R",
        writepv=f"{foc5_pv_root}Spd_S",
        precision=0.1,
        mapping={"14": 14, "7": 7, "0": 0},
        in_phase="foc5_chopper_phased",
        state="foc5_chopper_status",
    ),
    foc5_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv=f"{foc5_pv_root}ChopDly-S",
        writepv=f"{foc5_pv_root}ChopDly-S",
        abslimits=(0.0, 0.0),
    ),
    foc5_chopper_phase=device(
        "nicos_ess.devices.transformer_devices.ChopperPhase",
        description="The phase of the chopper.",
        phase_ns_dev="foc5_chopper_delay",
        mapped_speed_dev="foc5_chopper_speed",
        offset=0.0,
        unit="degrees",
    ),
    foc5_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv=f"{foc5_pv_root}DiffTSSamples",
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    foc5_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv=f"{foc5_pv_root}InPhaseTS-R",
    ),
    foc5_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Park angle: rotor position (Pos_R), park setpoint (Park_S).",
        readpv=f"{foc5_pv_root}Pos_R",
        writepv=f"{foc5_pv_root}Park_S",
        precision=0.5,
        visibility=(),
    ),
    foc5_chopper_park_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The park status for the WLS1 chopper.",
        readpv=f"{foc5_pv_root}ParkStatus_R",
    ),
    foc5_chopper_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the WLS1 chopper.",
        readpv=f"{foc5_pv_root}C_Park",
        writepv=f"{foc5_pv_root}C_Park",
    ),
    foc5_chopper_alarms=device(
        "nicos_ess.devices.epics.chopper.NewChopperAlarms",
        description="The chopper alarms",
        pv_root=foc5_pv_root,
        visibility=(),
    ),
    foc5_chopper_total_delay=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=(
            "The total delay (MechDly-S + BeamPosDly-S + ChopDly-S). "
            "The full delay that is applied on proton on target event for "
            "the driving signal of the chopper."
        ),
        readpv=f"{foc5_pv_root}TotDly",
        visibility=("metadata", "namespace"),
    ),
    foc5_chopper=device(
        "nicos_ess.devices.epics.chopper.NewEssChopperController",
        description="The chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="foc5_chopper_status",
        command="foc5_chopper_control",
        speed="foc5_chopper_speed",
        chic_conn="chpsy4_chopper_chic",
        alarms="foc5_chopper_alarms",
        total_delay="foc5_chopper_total_delay",
        park_angle="foc5_chopper_park_angle",
        delay_errors="foc5_chopper_delay_errors",
        slit_edges=[
            [0.0, 50.81],
            [62.36, 110.91],
            [120.83, 166.32],
            [176.995, 218.315],
            [229.21, 266.66],
            [278.355, 316.095],
        ],
        beam_position=42.36,
        resolver_sign=-1,
        tdc_resolver_position=0.0,
        distance=33.0,
        legacy_spd_sign=True,
    ),
    foc5_vacuum=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The vacuum pressure",
        readpv=f"{vacuum_pv_root}200:PrsR",
        fmtstr="%.2e",
    ),
)
