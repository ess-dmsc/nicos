description = "The mini-chopper for YMIR"

pv_root = "YMIR-ChpSy1:Chop-MIC-101:"
chic_root = "YMIR-ChpSy1:Chop-CHIC-001:"

devices = dict(
    mini_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The chopper status.",
        readpv="{}Chop_Stat".format(pv_root),
        visibility=(),
    ),
    mini_chopper_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Used to start and stop the chopper.",
        readpv="{}Cmd".format(pv_root),
        writepv="{}Cmd".format(pv_root),
        requires={"level": "admin"},
        visibility=(),
    ),
    mini_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current speed.",
        readpv="{}Spd_Stat".format(pv_root),
        writepv="{}Spd_SP".format(pv_root),
        abslimits=(0.0, 14),
        precision=0.1,
    ),
    mini_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(pv_root),
        writepv="{}ChopDly-S".format(pv_root),
        abslimits=(0.0, 71428571.0),
    ),
    mini_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The chopper's park angle.",
        readpv="{}ParkPos_Stat".format(pv_root),
        visibility=(),
    ),
    mini_chopper_vacuum_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The chopper vacuum",
        readpv="{}Vac_Stat".format(pv_root),
        visibility=(),
    ),
    mini_chopper_alarm_level=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper alarm status",
        readpv="{}Lvl_Alrm".format(chic_root),
        visibility=(),
    ),
    mini_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv="{}ConnectedR".format(chic_root),
        visibility=(),
    ),
    mini_chopper=device(
        "nicos_ess.devices.epics.chopper.EssChopperController",
        description="The mini-chopper controller",
        pollinterval=0.5,
        maxage=None,
        state="mini_chopper_status",
        command="mini_chopper_control",
        speed="mini_chopper_speed",
        chic_conn="mini_chopper_chic",
    ),
)
