description = "The choppers in chopper system 1 for ODIN"

wfmc1_pv_root = "ODIN-ChpSy1:Chop-WFMC-101:"
wfmc2_pv_root = "ODIN-ChpSy1:Chop-WFMC-102:"
foc1_pv_root = "ODIN-ChpSy1:Chop-FOC-101:"
bpc1_pv_root = "ODIN-ChpSy1:Chop-BPC-102:"
# chic_root = "TBL-ChpSy1:Chop-CHIC-001:"
vacuum_pv_root = "ODIN-VacBnkr:Vac-VGP-"

devices = dict(
    wfmc1_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(wfmc1_pv_root),
        visibility=(),
    ),
    wfmc1_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",  # Should be EpicsAnalogMoveable later
        description="The current speed.",
        readpv="{}Spd_R".format(wfmc1_pv_root),
        writepv="{}Spd_S".format(wfmc1_pv_root),
        precision=0.1,
        mapping={"14 Hz": 14, "7 Hz": 7, "-7 Hz": -7, "0 Hz": 0},
    ),
    wfmc1_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(wfmc1_pv_root),
        writepv="{}ChopDly-S".format(wfmc1_pv_root),
        abslimits=(0.0, 0.0),
    ),
    wfmc1_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(wfmc1_pv_root),
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    wfmc1_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(wfmc1_pv_root),
    ),
    wfmc1_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(wfmc1_pv_root),
        writepv="{}ParkAngle_S".format(wfmc1_pv_root),
    ),
    wfmc1_chopper=device(
        "nicos_ess.devices.epics.chopper.OdinChopperController",
        description="The chopper controller",
        pv_root=wfmc1_pv_root,
        monitor=True,
        slit_edges=[
            [0.0, 5.7],
            [48.65, 57.65],
            [94.32, 106.32],
            [137.1, 152.0],
            [177.27, 194.77],
            [214.91, 234.91],
        ],
        mapping={
            "Start": "start",
            "AStart": "a_start",
            "Stop": "stop",
            "Park": "park",
        },
    ),
    wfmc1_vacuum=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The vacuum pressure",
        readpv="{}100:PrsR".format(vacuum_pv_root),
        fmtstr="%.2e",
    ),
    wfmc2_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(wfmc2_pv_root),
        visibility=(),
    ),
    wfmc2_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The current speed.",
        readpv="{}Spd_R".format(wfmc2_pv_root),
        writepv="{}Spd_S".format(wfmc2_pv_root),
        precision=0.1,
        mapping={"14 Hz": 14, "7 Hz": 7, "-7 Hz": -7, "0 Hz": 0},
    ),
    wfmc2_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(wfmc2_pv_root),
        writepv="{}ChopDly-S".format(wfmc2_pv_root),
        abslimits=(0.0, 0.0),
    ),
    wfmc2_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(wfmc2_pv_root),
        unit="ns",
        visibility=("metadata", "namespace"),
    ),
    wfmc2_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(wfmc2_pv_root),
    ),
    wfmc2_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(wfmc2_pv_root),
        writepv="{}ParkAngle_S".format(wfmc2_pv_root),
    ),
    wfmc2_chopper=device(
        "nicos_ess.devices.epics.chopper.OdinChopperController",
        description="The chopper controller",
        pv_root=wfmc2_pv_root,
        monitor=True,
        slit_edges=[
            [0.0, 5.7],
            [51.89, 60.89],
            [100.59, 112.59],
            [146.21, 161.11],
            [189.05, 206.55],
            [229.19, 249.19],
        ],
        mapping={"Start": "start", "AStart": "a_start", "Stop": "stop", "Park": "park"},
    ),
    wfmc2_vacuum=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The vacuum pressure",
        readpv="{}101:PrsR".format(vacuum_pv_root),
        fmtstr="%.2e",
    ),
    foc1_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(foc1_pv_root),
        visibility=(),
    ),
    foc1_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The current speed.",
        readpv="{}Spd_R".format(foc1_pv_root),
        writepv="{}Spd_S".format(foc1_pv_root),
        precision=0.1,
        mapping={"14 Hz": 14, "7 Hz": 7, "-7 Hz": -7, "0 Hz": 0},
    ),
    foc1_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(foc1_pv_root),
        writepv="{}ChopDly-S".format(foc1_pv_root),
        abslimits=(0.0, 0.0),
    ),
    foc1_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(foc1_pv_root),
        unit="ns",
        visibility=("metadata", "namespace"),
    ),
    foc1_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(foc1_pv_root),
    ),
    foc1_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(foc1_pv_root),
        writepv="{}ParkAngle_S".format(foc1_pv_root),
    ),
    foc1_chopper=device(
        "nicos_ess.devices.epics.chopper.OdinChopperController",
        description="The chopper controller",
        pv_root=foc1_pv_root,
        monitor=True,
        slit_edges=[
            [0.0, 11.06],
            [45.7, 58.76],
            [88.54, 103.48],
            [128.715, 145.425],
            [166.39, 184.75],
            [204.9, 221.62],
        ],
        mapping={"Start": "start", "AStart": "a_start", "Stop": "stop", "Park": "park"},
    ),
    foc1_vacuum=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The vacuum pressure",
        readpv="{}102:PrsR".format(vacuum_pv_root),
        fmtstr="%.2e",
    ),
    bpc1_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(bpc1_pv_root),
        visibility=(),
    ),
    bpc1_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The current speed.",
        readpv="{}Spd_R".format(bpc1_pv_root),
        writepv="{}Spd_S".format(bpc1_pv_root),
        precision=0.1,
        mapping={"14 Hz": 14, "7 Hz": 7, "-7 Hz": -7, "0 Hz": 0},
    ),
    bpc1_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(bpc1_pv_root),
        writepv="{}ChopDly-S".format(bpc1_pv_root),
        abslimits=(0.0, 0.0),
    ),
    bpc1_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(bpc1_pv_root),
        unit="ns",
        visibility=("metadata", "namespace"),
    ),
    bpc1_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(bpc1_pv_root),
    ),
    bpc1_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(bpc1_pv_root),
        writepv="{}ParkAngle_S".format(bpc1_pv_root),
    ),
    bpc1_chopper=device(
        "nicos_ess.devices.epics.chopper.OdinChopperController",
        description="The chopper controller",
        pv_root=bpc1_pv_root,
        monitor=True,
        slit_edges=[[0.0, 46.71]],
        mapping={"Start": "start", "AStart": "a_start", "Stop": "stop", "Park": "park"},
    ),
    bpc1_vacuum=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The vacuum pressure",
        readpv="{}102:PrsR".format(vacuum_pv_root),  # same as foc
        fmtstr="%.2e",
    ),
)
