description = "NMX WLS-2 Chopper disc 1 (double disc)"

pv_root_1 = "NMX-ChpSy1:Chop-WLS-201:"
chic_root = "NMX-ChpSy1:Chop-CHIC-001:"

devices = dict(
    status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(pv_root_1),
        visibility=(),
    ),
    control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv="{}C_Execute".format(pv_root_1),
        writepv="{}C_Execute".format(pv_root_1),
        requires={"level": "admin"},
        visibility=(),
    ),
    speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The current speed.",
        readpv="{}Spd_R".format(pv_root_1),
        writepv="{}Spd_S".format(pv_root_1),
        precision=0.1,
        mapping={"0 Hz": 0, "14 Hz": 14},
    ),
    delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(pv_root_1),
        writepv="{}ChopDly-S".format(pv_root_1),
        abslimits=(0.0, 0.0),
    ),
    phase=device(
        "nicos_ess.devices.transformer_devices.ChopperPhase",
        description="The phase of the chopper.",
        phase_ns_dev="delay",
        mapped_speed_dev="speed",
        offset=0,
        unit="degrees",
    ),
    delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(pv_root_1),
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(pv_root_1),
    ),
    park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(pv_root_1),
        writepv="{}Park_S".format(pv_root_1),
        visibility=(),
        mapping={
            "park pos 0": 0,
            "park pos 1": 90,
            "park pos 2": 180,
            "park pos 3": 270,
        },
    ),
    park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the WLS-2A chopper.",
        readpv="{}C_Park".format(pv_root_1),
        writepv="{}C_Park".format(pv_root_1),
    ),
    chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv="{}ConnectedR".format(chic_root),
        visibility=(),
        pva=True,
    ),
    alarms=device(
        "nicos_ess.devices.epics.chopper.ChopperAlarms",
        description="The chopper alarms",
        pv_root=pv_root_1,
        visibility=(),
    ),
    chopper=device(
        "nicos_ess.devices.epics.chopper.EssChopperController",
        description="The chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="status",
        command="control",
        speed="speed",
        chic_conn="chic",
        alarms="alarms",
        slit_edges=[[0, 170]],
        resolver_offset=158.0,
        tdc_offset=176.3,
        spin_direction="CCW",
    ),
)
