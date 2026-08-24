description = "ARINAX controls (sample exposure system)"

group = "optional"

# pv_root = "NMX-mockup:"
pv_root = "NMX-ExpSys::"  # EPICS proxy production PVs

SAMPLE_STORAGE = {
    f"Sample Storage {s} - SS{i}": (f"Sample_Storage_{s}", f"SS{i}")
    for s in range(1, 4)
    for i in range(1, 11)
}

UNIPUCKS = {
    f"UniPuck {s} - UP{i}": (f"UniPuck{s}", f"UP{i}")
    for s in range(1, 3)
    for i in range(1, 17)
}

ZOOM_LEVELS = {f"Zoom level {l}": l for l in range(1, 8)}

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
    # DPU Config
    detector_config=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="ARINAX DPU Configuration",
        readpv=f"{pv_root}getDPUConfiguration",
        writepv=f"{pv_root}setDPUConfiguration",
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
    # Sample load
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
    # TODO: Still to be solved/included in the proxy IOC!
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
    # Sample centring motion
    # Using numbers to have the same order from ARINAX GUI
    sample_centring_1_phi=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample centring motor Phi",
        readpv=f"{pv_root}getPhiPosition",
        writepv=f"{pv_root}setPhiPosition",
        # unit="deg",
    ),
    sample_centring_2_chi=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample centring motor Chi",
        readpv=f"{pv_root}getChiPosition",
        writepv=f"{pv_root}setChiPosition",
        # unit="mm",
    ),
    sample_centring_3_theta=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample centring motor Theta",
        readpv=f"{pv_root}getThetaPosition",
        writepv=f"{pv_root}setThetaPosition",
        # unit="mm",
    ),
    # Alignment table motion
    # TODO: Add the set PVs below to the proxy.
    alignment_table_x=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor X",
        readpv=f"{pv_root}getAlignmentTableXPosition",
        writepv=f"{pv_root}setAlignmentTableXPosition",
    ),
    alignment_table_y=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor Y",
        readpv=f"{pv_root}getAlignmentTableYPosition",
        writepv=f"{pv_root}setAlignmentTableYPosition",
    ),
    alignment_table_z=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor Z",
        readpv=f"{pv_root}getAlignmentTableZPosition",
        writepv=f"{pv_root}setAlignmentTableZPosition",
    ),
    # TODO: Add AlignmentTable Vx, Vy, Vfocus to the proxy.
    alignment_table_vx=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor Vx",
        readpv=f"{pv_root}getAlignmentTableVxPosition",
        writepv=f"{pv_root}setAlignmentTableVxPosition",
    ),
    alignment_table_vy=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor Vy",
        readpv=f"{pv_root}getAlignmentTableVyPosition",
        writepv=f"{pv_root}setAlignmentTableVyPosition",
    ),
    alignment_table_vFocus=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX alignment table motor Vfocus",
        readpv=f"{pv_root}getAlignmentTableVfocusPosition",
        writepv=f"{pv_root}setAlignmentTableVfocusPosition",
    ),
    # Centring table motion
    centring_table_x=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX centring table motor X",
        readpv=f"{pv_root}getCentringTableXPosition",
        writepv=f"{pv_root}setCentringTableXPosition",
    ),
    centring_table_y=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX centring table motor Y",
        readpv=f"{pv_root}getCentringTableYPosition",
        writepv=f"{pv_root}setCentringTableYPosition",
    ),
    # Backlight
    # TODO: This can possibly be changed to (manual) mapped device once we know its real limits.
    backlight_level=device(
        "nicos_ess.devices.epics.pva.EpicsDigitalMoveable",
        description="ARINAX SPU backlight level",
        readpv=f"{pv_root}getBackLightLevel",
        writepv=f"{pv_root}setBackLightLevel",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        userlimits=[0, 100],
        fmtstr="%d",
    ),
    backlight_position=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX SPU backlight position",
        readpv=f"{pv_root}getBackLightPOS",
        writepv=f"{pv_root}setBackLightPOS",
    ),
    # Zoom
    zoom_level=device(
        # The zoom range is on the :getZoomRange PV.
        "nicos_ess.devices.epics.pva.EpicsManualMappedMoveable",
        description="ARINAX SPU zoom level",
        readpv=f"{pv_root}getZoomLevel",
        writepv=f"{pv_root}setZoomLevel",
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping=ZOOM_LEVELS,
    ),
)
