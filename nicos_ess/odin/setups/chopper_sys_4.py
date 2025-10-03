description = "The choppers in chopper system 4 for ODIN"

foc5_pv_root = "ODIN-ChpSy4:Chop-FOC-501:"
# chic_root = "TBL-ChpSy1:Chop-CHIC-001:"
vacuum_pv_root = "ODIN-VacInstr:Vac-VGP-"


devices = dict(
    foc5_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(foc5_pv_root),
        visibility=(),
    ),
    foc5_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",  # Should be EpicsAnalogMoveable later
        description="The current speed.",
        readpv="{}Spd_R".format(foc5_pv_root),
        writepv="{}Spd_S".format(foc5_pv_root),
        precision=0.1,
        mapping={"14 Hz": 14, "7 Hz": 7, "-7 Hz": -7, "0 Hz": 0},
    ),
    foc5_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(foc5_pv_root),
        writepv="{}ChopDly-S".format(foc5_pv_root),
        abslimits=(0.0, 0.0),
    ),
    foc5_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(foc5_pv_root),
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    foc5_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(foc5_pv_root),
    ),
    foc5_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(foc5_pv_root),
        writepv="{}ParkAngle_S".format(foc5_pv_root),
    ),
    foc5_chopper=device(
        "nicos_ess.devices.epics.chopper.OdinChopperController",
        description="The chopper controller",
        pv_root=foc5_pv_root,
        monitor=True,
        slit_edges=[
            [0.0, 50.81],
            [62.365, 110.905],
            [120.83, 166.32],
            [176.995, 218.315],
            [229.21, 266.66],
            [278.355, 316.095],
        ],
        mapping={
            "Start": "start",
            "AStart": "a_start",
            "Stop": "stop",
            "Park": "park",
        },
        speed="foc5_chopper_speed",
    ),
    foc5_vacuum=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The vacuum pressure",
        readpv="{}200:PrsR".format(vacuum_pv_root),
        fmtstr="%.2e",
    ),
)
