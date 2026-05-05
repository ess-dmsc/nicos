description = "NMX WLS-2 Chopper disc 2 (double disc)"

pv_root_2 = "NMX-ChpSy1:Chop-WLS-202:"
chic_root = "NMX-ChpSy1:Chop-CHIC-001:"

devices = dict(
    wls2b_chopper_log=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The logs from chopper controller",
        readpv="{}Log_R".format(pv_root_2),
        visibility=(),
    ),
    wls2b_chopper_levitation_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}LeviStatus_R".format(pv_root_2),
        visibility=(),
    ),
    wls2b_chopper_motor_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the motor of the chopper",
        readpv="{}MtrTemp_R".format(pv_root_2),
        visibility=(),
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
    wls2b_chopper_total_delay=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=(
            "The total delay (MechDly-S + BeamPosDly-S + ChopDly-S). "
            "The full delay that is applied on proton on target event for "
            "the driving signal of the chopper."
        ),
        readpv="{}TotDly".format(pv_root_2),
        visibility=(
            "metadata",
            "namespace",
        ),
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
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(pv_root_2),
        writepv="{}Park_S".format(pv_root_2),
        visibility=(),
        mapping={
            "park open": 165.0,
            "park close": 345.0,
        },
    ),
    wls2b_chopper_park_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The park status for the WLS-2B chopper.",
        readpv="{}ParkStatus_R".format(pv_root_2),
    ),
    wls2b_chopper_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the WLS-2B chopper.",
        readpv="{}C_Park".format(pv_root_2),
        writepv="{}C_Park".format(pv_root_2),
    ),
    wls2b_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv="{}ConnectedR".format(chic_root),
        visibility=(),
    ),
    wls2b_chopper_alarms=device(
        "nicos_ess.devices.epics.chopper.ChopperAlarmsV2",
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
        total_delay="wls2b_chopper_total_delay",
        park_angle="wls2b_chopper_park_angle",
        delay_errors="wls2b_chopper_delay_errors",
        chic_conn="wls2b_chopper_chic",
        alarms="wls2b_chopper_alarms",
        slit_edges=[[0.0, 170.0]],
        motor_position="downstream",
        tdc_resolver_position=342.5,
        park_open_angle=165.0,
        disk_delay=0.0,
    ),
)
