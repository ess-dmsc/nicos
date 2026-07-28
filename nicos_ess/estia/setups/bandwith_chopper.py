description = "ESTIA Bandwidth Chopper"

pv_root = "ESTIA-ChpSy1:Chop-BWC-101:"
chic_root = "ESTIA-ChpSy1:Chop-CHIC-001:"

devices = dict(
    bwc_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv=f"{pv_root}ChopState_R",
        visibility=(),
    ),
    bwc_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv=f"{pv_root}C_ExecuteUser",
        writepv=f"{pv_root}C_ExecuteUser",
        requires={"level": "admin"},
        visibility=(),
    ),
    bwc_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The current speed.",
        readpv=f"{pv_root}Spd_R",
        writepv=f"{pv_root}Spd_S",
        precision=0.1,
        mapping={"14 Hz": 14, "7 Hz": 7, "4⅔ Hz": 4.666666667, "0 Hz": 0},
    ),
    bwc_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv=f"{pv_root}ChopDly-S",
        writepv=f"{pv_root}ChopDly-S",
        abslimits=(0.0, 0.0),
    ),
    bwc_phase=device(
        "nicos_ess.devices.transformer_devices.ChopperPhase",
        description="The phase of the chopper.",
        phase_ns_dev="bwc_delay",
        mapped_speed_dev="bwc_speed",
        offset=0,
        unit="degrees",
    ),
    bwc_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv=f"{pv_root}DiffTSSamples",
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    bwc_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv=f"{pv_root}InPhaseTS-R",
    ),
    bwc_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The chopper's park angle.",
        readpv=f"{pv_root}Pos_R",
        writepv=f"{pv_root}Park_S",
        visibility=(),
        mapping={
            "park pos 0": 0,
            "park pos 1": 45,
            "park pos 2": 90,
            "park pos 3": 180,
        },
    ),
    bwc_park_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The park status for the BWC1 chopper.",
        readpv=f"{pv_root}ParkStatus_R",
    ),
    bwc_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the BWC chopper.",
        readpv=f"{pv_root}C_Park",
        writepv=f"{pv_root}C_Park",
    ),
    bwc_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv=f"{chic_root}ConnectedR",
        visibility=(),
        pva=True,
    ),
    bwc_alarms=device(
        "nicos_ess.devices.epics.chopper.NewChopperAlarms",
        description="The chopper alarms",
        pv_root=pv_root,
        visibility=(),
    ),
    bwc=device(
        "nicos_ess.devices.epics.chopper.NewEssChopperController",
        description="The chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="bwc_status",
        command="bwc_control",
        speed="bwc_speed",
        chic_conn="bwc_chic",
        alarms="bwc_alarms",
        slit_edges=[[0, 98]],
        resolver_offset=-301,
        tdc_offset=0,
    ),
)
