description = "The mini-chopper for YMIR"

pv_root = "YMIR-ChpSy1:Chop-MIC-101:"
chic_root = "YMIR-ChpSy1:Chop-CHIC-001:"

devices = dict(
    mini_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(pv_root),
        visibility=(),
    ),
    mini_chopper_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv="{}C_ExecuteUser".format(pv_root),
        writepv="{}C_ExecuteUser".format(pv_root),
        requires={"level": "admin"},
        visibility=(),
    ),
    mini_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The current speed.",
        readpv="{}Spd_R".format(pv_root),
        writepv="{}Spd_S".format(pv_root),
        abslimits=(0.0, 14),
        precision=0.1,
        mapping={"14 Hz": 14, "7 Hz": 7, "0 Hz": 0},
    ),
    mini_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(pv_root),
        writepv="{}ChopDly-S".format(pv_root),
        abslimits=(0.0, 71428571.0),
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
        readpv="{}DiffTSSamples".format(pv_root),
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    mini_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhaseTS-R".format(pv_root),
        maxage=0,
    ),
    mini_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(pv_root),
        writepv="{}Park_S".format(pv_root),
        visibility=(),
        mapping={
            "park pos 0": 0,
            "park pos 1": 45,
            "park pos 2": 90,
            "park pos 3": 180,
        },
    ),
    mini_chopper_park_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The park status for the mini chopper.",
        readpv="{}ParkStatus_R".format(pv_root),
    ),
    mini_chopper_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the mini chopper.",
        readpv="{}C_Park".format(pv_root),
        writepv="{}C_Park".format(pv_root),
    ),
    mini_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv="{}ConnectedR".format(chic_root),
        visibility=(),
    ),
    mini_chopper_alarms=device(
        "nicos_ess.devices.epics.chopper.NewChopperAlarms",
        description="The chopper alarms",
        pv_root=pv_root,
        visibility=(),
    ),
    mini_chopper=device(
        "nicos_ess.devices.epics.chopper.NewEssChopperController",
        description="The mini-chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="mini_chopper_status",
        command="mini_chopper_control",
        speed="mini_chopper_speed",
        chic_conn="mini_chopper_chic",
    ),
)
