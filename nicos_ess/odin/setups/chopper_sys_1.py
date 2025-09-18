description = "The choppers in chopper system 1 for ODIN"

pv_root_1 = "ODIN-ChpSy1:Chop-WFMC-101:"
# chic_root = "TBL-ChpSy1:Chop-CHIC-001:"

devices = dict(
    bwc1_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(pv_root_1),
        visibility=(),
    ),
    bwc1_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",  # Should be EpicsAnalogMoveable later
        description="The current speed.",
        readpv="{}Spd_R".format(pv_root_1),
        # writepv="{}Spd_S".format(pv_root_1),
        # abslimits=(0.0, 0.0),
        # precision=0.1,
    ),
    bwc1_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(pv_root_1),
        writepv="{}ChopDly-S".format(pv_root_1),
        abslimits=(0.0, 0.0),
    ),
    bwc1_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(pv_root_1),
        unit="ns",
        visibility=(
            "metadata",
            "namespace",
        ),
    ),
    bwc1_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(pv_root_1),
    ),
    bwc1_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",  # Should be EpicsAnalogMoveable later
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(pv_root_1),
        # writepv="{}Park_S".format(pv_root_1),
        # visibility=(),
    ),
    bwc1_chopper=device(
        "nicos_ess.devices.epics.chopper.Chopper",
        description="The chopper controller",
        pv_root=pv_root_1,
        monitor=True,
        slit_edges=[[0.0, 170.0]],
        mapping={
            "Start": "start",
            "AStart": "a_start",
            "Stop": "stop",
            "Park": "park",
        },
    ),
)
