description = "NMX WLS-1 Chopper (single disc)"

pv_root_1 = "NMX-ChpSy1:Chop-WLS-101:"
# pv_root_2 = ""
chic_root = "NMX-ChpSy1:Chop-CHIC-001:"

devices = dict(
    wls1_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(pv_root_1),
        visibility=(),
    ),
    wls1_chopper_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv="{}C_Execute".format(pv_root_1),
        writepv="{}C_Execute".format(pv_root_1),
        requires={"level": "admin"},
        visibility=(),
    ),
    wls1_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The current speed.",
        readpv="{}Spd_R".format(pv_root_1),
        writepv="{}Spd_S".format(pv_root_1),
        precision=0.1,
        mapping={"0 Hz": 0, "14 Hz": 14},
    ),
    wls1_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(pv_root_1),
        writepv="{}ChopDly-S".format(pv_root_1),
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
        readpv="{}DiffTSSamples".format(pv_root_1),
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    wls1_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(pv_root_1),
    ),
    wls1_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(pv_root_1),
        writepv="{}Park_S".format(pv_root_1),
        visibility=(),
    ),
    wls1_chopper_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the WLS1 chopper.",
        readpv="{}ParkPos_S".format(pv_root_1),
        writepv="{}ParkPos_S".format(pv_root_1),
    ),
    wls1_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv="{}ConnectedR".format(chic_root),
        visibility=(),
        pva=True,
    ),
    wls1_chopper_alarms=device(
        "nicos_ess.devices.epics.chopper.ChopperAlarms",
        description="The chopper alarms",
        pv_root=pv_root_1,
        visibility=(),
    ),
    wls1_chopper=device(
        "nicos_ess.devices.epics.chopper.EssChopperController",
        description="The chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="wls1_chopper_status",
        command="wls1_chopper_control",
        speed="wls1_chopper_speed",
        chic_conn="wls1_chopper_chic",
        alarms="wls1_chopper_alarms",
        slit_edges=[[0, 170]],
        resolver_offset=-110.0,
        tdc_offset=-62.5,
    ),
)
