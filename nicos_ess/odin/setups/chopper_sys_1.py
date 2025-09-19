description = "The choppers in chopper system 1 for ODIN"

wfmc1_pv_root = "ODIN-ChpSy1:Chop-WFMC-101:"
wfmc2_pv_root = "ODIN-ChpSy1:Chop-WFMC-102:"
foc_pv_root = "ODIN-ChpSy1:Chop-FOC-101:"
bpc_pv_root = "ODIN-ChpSy1:Chop-BPC-102:"
# chic_root = "TBL-ChpSy1:Chop-CHIC-001:"

devices = dict(
    wfmc1_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(wfmc1_pv_root),
        visibility=(),
    ),
    wfmc1_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",  # Should be EpicsAnalogMoveable later
        description="The current speed.",
        readpv="{}Spd_R".format(wfmc1_pv_root),
        # writepv="{}Spd_S".format(pv_root_1),
        # abslimits=(0.0, 0.0),
        # precision=0.1,
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
        "nicos_ess.devices.epics.pva.EpicsReadable",  # Should be EpicsAnalogMoveable later
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(wfmc1_pv_root),
        # writepv="{}Park_S".format(pv_root_1),
        # visibility=(),
    ),
    wfmc1_chopper=device(
        "nicos_ess.devices.epics.chopper.OdinChopperController",
        description="The chopper controller",
        pv_root=wfmc1_pv_root,
        monitor=True,
        slit_edges=[
            [89.08, 94.78],
            [137.73, 146.73],
            [183.4, 195.4],
            [226.18, 241.08],
            [266.35, 283.85],
            [303.99, 323.99],
        ],
        mapping={
            "Start": "start",
            "AStart": "a_start",
            "Stop": "stop",
            "Park": "park",
        },
    ),
    wfmc2_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(wfmc2_pv_root),
        visibility=(),
    ),
    wfmc2_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The current speed.",
        readpv="{}Spd_R".format(wfmc2_pv_root),
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
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(wfmc2_pv_root),
    ),
    wfmc2_chopper=device(
        "nicos_ess.devices.epics.chopper.OdinChopperController",
        description="The chopper controller",
        pv_root=wfmc2_pv_root,
        monitor=True,
        slit_edges=[
            [94.82, 100.52],
            [146.71, 155.71],
            [195.41, 207.41],
            [241.03, 255.93],
            [283.87, 301.37],
            [324.01, 344.01],
        ],
        mapping={"Start": "start", "AStart": "a_start", "Stop": "stop", "Park": "park"},
    ),
    foc1_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(foc_pv_root),
        visibility=(),
    ),
    foc1_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The current speed.",
        readpv="{}Spd_R".format(foc_pv_root),
    ),
    foc1_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(foc_pv_root),
        writepv="{}ChopDly-S".format(foc_pv_root),
        abslimits=(0.0, 0.0),
    ),
    foc1_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(foc_pv_root),
        unit="ns",
        visibility=("metadata", "namespace"),
    ),
    foc1_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(foc_pv_root),
    ),
    foc1_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(foc_pv_root),
    ),
    foc1_chopper=device(
        "nicos_ess.devices.epics.chopper.OdinChopperController",
        description="The chopper controller",
        pv_root=foc_pv_root,
        monitor=True,
        slit_edges=[
            [75.59, 86.65],
            [121.29, 134.35],
            [164.13, 179.07],
            [204.305, 221.015],
            [241.98, 260.34],
            [280.49, 297.21],
        ],
        mapping={"Start": "start", "AStart": "a_start", "Stop": "stop", "Park": "park"},
    ),
    bpc_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(bpc_pv_root),
        visibility=(),
    ),
    bpc_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The current speed.",
        readpv="{}Spd_R".format(bpc_pv_root),
    ),
    bpc_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(bpc_pv_root),
        writepv="{}ChopDly-S".format(bpc_pv_root),
        abslimits=(0.0, 0.0),
    ),
    bpc_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(bpc_pv_root),
        unit="ns",
        visibility=("metadata", "namespace"),
    ),
    bpc_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(bpc_pv_root),
    ),
    bpc_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(bpc_pv_root),
    ),
    bpc_chopper=device(
        "nicos_ess.devices.epics.chopper.OdinChopperController",
        description="The chopper controller",
        pv_root=bpc_pv_root,
        monitor=True,
        slit_edges=[[7.375, 54.085]],
        mapping={"Start": "start", "AStart": "a_start", "Stop": "stop", "Park": "park"},
    ),
)
