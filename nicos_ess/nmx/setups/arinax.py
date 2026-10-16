description = "ARINAX controls (sample exposure system)"

group = "optional"

pv_root = "NMX-ExpSys::"  # The EPICS proxy IOC that interfaces ARINAX PVs.

SAMPLE_STORAGE = {
    f"Sample Storage {s} - SS{i}": f"Sample_Storage_{s} SS{i}"
    for s in range(1, 4)
    for i in range(1, 11)
}

UNIPUCKS = {
    f"UniPuck {s} - UP{i}": f"UniPuck{s} UP{i}"
    for s in range(1, 3)
    for i in range(1, 17)
}

ZOOM_LEVELS = {f"Zoom level {i}": i for i in range(1, 8)}
LIGHT_LEVELS = {f"Light level {i}": i * 5 for i in range(0, 11)}
PRECISION = 0.001

devices = dict(
    # General statue/status of ARINAX system
    arinax_state=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX System State",
        readpv=f"{pv_root}getState",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    arinax_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="ARINAX System Status",
        readpv=f"{pv_root}getStatus",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    # DPU and SPU Config
    config_detector_position=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="ARINAX DPU Configuration",
        readpv=f"{pv_root}getDPUConfiguration",
        writepv=f"{pv_root}setDPUConfiguration",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    config_sample_holder_position=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="ARINAX SPU Configuration",
        readpv=f"{pv_root}getSPUConfiguration",
        writepv=f"{pv_root}setSPUConfiguration",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    # Sample tool
    tool_currently_mounted=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX SPU current mounted tool",
        readpv=f"{pv_root}getCurrentTool",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    tool_load=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Select and load an ARINAX SPU tool",
        readpv=f"{pv_root}getCurrentTool",
        writepv=f"{pv_root}LoadTool",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    # Sample loading
    sample_load_from_SS=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedMoveable",
        description="Select and load an ARINAX SPU sample from storage",
        readpv=f"{pv_root}LoadSSSample",
        writepv=f"{pv_root}LoadSSSample",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping=SAMPLE_STORAGE,
    ),
    sample_load_from_UP=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedMoveable",
        description="Select and load an ARINAX SPU sample from unipuck",
        readpv=f"{pv_root}LoadUPSample",
        writepv=f"{pv_root}LoadUPSample",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping=UNIPUCKS,
    ),
    sample_is_loaded=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Whether ARINAX SPU sample is mounted or not",
        readpv=f"{pv_root}getIsSampleLoaded",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    # TODO: Placeholder. To be included in the proxy IOC.
    sample_unload=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedMoveable",
        description="Unload ARINAX SPU sample",
        readpv=f"{pv_root}UnLoadSample",
        writepv=f"{pv_root}UnLoadSample",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping={
            "Unload sample": "1",  # String PV. Preferably use "0" or "1".
        },
    ),
    # Sample centring motion (using numbers to have the same order from ARINAX GUI)
    sample_centring_1_phi=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample centring motor Phi",
        readpv=f"{pv_root}getPhiPosition",
        writepv=f"{pv_root}setPhiPosition",
        precision=PRECISION,
    ),
    sample_centring_2_chi=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample centring motor Chi",
        readpv=f"{pv_root}getChiPosition",
        writepv=f"{pv_root}setChiPosition",
        precision=PRECISION,
    ),
    sample_centring_3_theta=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample centring motor Theta",
        readpv=f"{pv_root}getThetaPosition",
        writepv=f"{pv_root}setThetaPosition",
        precision=PRECISION,
    ),
    # Alignment table motion
    alignment_table_x=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor X",
        readpv=f"{pv_root}getAlignmentTableXPosition",
        writepv=f"{pv_root}setAlignmentTableXPosition",
        precision=PRECISION,
    ),
    alignment_table_y=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor Y",
        readpv=f"{pv_root}getAlignmentTableYPosition",
        writepv=f"{pv_root}setAlignmentTableYPosition",
        precision=PRECISION,
    ),
    alignment_table_z=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor Z",
        readpv=f"{pv_root}getAlignmentTableZPosition",
        writepv=f"{pv_root}setAlignmentTableZPosition",
        precision=PRECISION,
    ),
    alignment_table_vx=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor Vx",
        readpv=f"{pv_root}getAlignmentTableVxPosition",
        writepv=f"{pv_root}setAlignmentTableVxPosition",
        precision=PRECISION,
    ),
    alignment_table_vy=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor Vy",
        readpv=f"{pv_root}getAlignmentTableVyPosition",
        writepv=f"{pv_root}setAlignmentTableVyPosition",
        precision=PRECISION,
    ),
    alignment_table_vFocus=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor Vfocus",
        readpv=f"{pv_root}getAlignmentTableVfocusPosition",
        writepv=f"{pv_root}setAlignmentTableVfocusPosition",
        precision=PRECISION,
    ),
    # Centring table motion
    centring_table_x=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX centring table motor X",
        readpv=f"{pv_root}getCentringTableXPosition",
        writepv=f"{pv_root}setCentringTableXPosition",
        precision=PRECISION,
    ),
    centring_table_y=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX centring table motor Y",
        readpv=f"{pv_root}getCentringTableYPosition",
        writepv=f"{pv_root}setCentringTableYPosition",
        precision=PRECISION,
    ),
    # Backlight
    backlight_level=device(
        # This PV goes from 0 to 100, but steps of 10 makes more sense.
        # NOTE: The control is for now setting double of the input value,
        # e.g., setting 5 makes the control goes to 10. Checking if it's an issue.
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="ARINAX SPU backlight level",
        readpv=f"{pv_root}getBackLightLevel",
        writepv=f"{pv_root}setBackLightLevel",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        fmtstr="%d",
        mapping=LIGHT_LEVELS,
    ),
    backlight_position=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedMoveable",
        description="ARINAX SPU backlight position",
        readpv=f"{pv_root}getBackLightPOS",
        writepv=f"{pv_root}setBackLightPOS",
        fmtstr="%d",
        mapping={"Out": 0, "In": 1},
    ),
    # Zoom
    zoom_level=device(
        # The zoom range is on the :getZoomRange PV.
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="ARINAX SPU zoom level",
        readpv=f"{pv_root}getZoomLevel",
        writepv=f"{pv_root}setZoomLevel",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        fmtstr="%d",
        mapping=ZOOM_LEVELS,
    ),
)
