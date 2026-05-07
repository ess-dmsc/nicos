description = "NMX WLS-1 Chopper (single disc)"

pv_root_1 = "NMX-ChpSy1:Chop-WLS-101:"
# pv_root_2 = ""
chic_root = "NMX-ChpSy1:Chop-CHIC-001:"

devices = dict(
    wls1_chopper_log=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The logs from chopper controller",
        readpv=f"{pv_root_1}Log_R",
        visibility=(),
    ),
    wls1_chopper_levitation_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv=f"{pv_root_1}LeviStatus_R",
        visibility=(),
    ),
    wls1_chopper_motor_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the motor of the chopper",
        readpv=f"{pv_root_1}MtrTemp_R",
        visibility=(),
    ),
    wls1_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv=f"{pv_root_1}ChopState_R",
        visibility=(),
    ),
    wls1_chopper_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv=f"{pv_root_1}C_Execute",
        writepv=f"{pv_root_1}C_Execute",
        requires={"level": "admin"},
        visibility=(),
    ),
    wls1_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The current speed.",
        readpv=f"{pv_root_1}Spd_R",
        writepv=f"{pv_root_1}Spd_S",
        precision=0.1,
        mapping={"0 Hz": 0, "14 Hz": 14},
    ),
    wls1_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv=f"{pv_root_1}ChopDly-S",
        writepv=f"{pv_root_1}ChopDly-S",
        abslimits=(0.0, 0.0),
    ),
    wls1_chopper_phase=device(
        "nicos_ess.devices.transformer_devices.ChopperPhase",
        description="The phase of the chopper.",
        phase_ns_dev="wls1_chopper_delay",
        mapped_speed_dev="wls1_chopper_speed",
        offset=0,
        unit="degrees",
    ),
    wls1_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv=f"{pv_root_1}DiffTSSamples",
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    wls1_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv=f"{pv_root_1}InPhs_R",
    ),
    wls1_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The chopper's park angle.",
        readpv=f"{pv_root_1}Pos_R",
        writepv=f"{pv_root_1}Park_S",
        visibility=(),
        mapping={
            "park pos 0": 0,
            "park pos 1": 90,
            "park pos 2": 180,
            "park pos 3": 270,
        },
    ),
    wls1_chopper_park_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The park status for the WLS1 chopper.",
        readpv=f"{pv_root_1}ParkStatus_R",
    ),
    wls1_chopper_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the WLS1 chopper.",
        readpv=f"{pv_root_1}C_Park",
        writepv=f"{pv_root_1}C_Park",
    ),
    wls1_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv=f"{chic_root}ConnectedR",
        visibility=(),
        pva=True,
    ),
    wls1_chopper_alarms=device(
        "nicos_ess.devices.epics.chopper.NmxChopperAlarms",
        description="The chopper alarms",
        pv_root=pv_root_1,
        visibility=(),
    ),
    wls1_chopper=device(
        "nicos_ess.devices.epics.chopper.NmxChopperController",
        description="The chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="wls1_chopper_status",
        command="wls1_chopper_control",
        speed="wls1_chopper_speed",
        chic_conn="wls1_chopper_chic",
        alarms="wls1_chopper_alarms",
        slit_edges=[[0, 170]],
        resolver_offset=280.0,
        tdc_offset=232.5,
        spin_direction="CCW",
    ),
)
