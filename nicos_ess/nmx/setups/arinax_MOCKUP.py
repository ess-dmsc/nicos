description = "ARINAX controls (from the mockup software)"

group = "optional"

pv_root = "NMX:"

SAMPLE_STORAGE = {
    f'Sample Storage {s} - SS{i}': (f"Sample_Storage_{s}", f"SS{i}")  
    for s in range(1,4)
    for i in range(1,11)
}

UNIPUCKS = {
    f'UniPuck {s} - UP{i}': (f"UniPuck{s}", f"UP{i}")  
    for s in range(1,3)
    for i in range(1,17)
}

devices = dict(
    # General Status of ARINAX system
    arinax_state=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX System State (mockup)",
        readpv=f"{pv_root}getState",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    arinax_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="ARINAX System Status (mockup)",
        readpv=f"{pv_root}getStatus",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    # DPU Config
    detector_config_control=device(
        "nicos_ess.nmx.devices.arinax.ConfigurableEpicsMappedMoveable",
        description="ARINAX DPU Configuration, control (mockup)",
        readpv=f"{pv_root}getDPUConfiguration",
        writepv=f"{pv_root}setDPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        write_enum_string=True,
    ),
    detector_config_readback=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX DPU Configuration, readback (mockup)",
        readpv=f"{pv_root}getDPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility=(),
    ),
    detector_config_setpoint=device(
        # Just for testing, coudl be removed later.
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="ARINAX DPU Configuration, setpoint readback (mockup)",
        readpv=f"{pv_root}setDPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility=(),
    ),
    # Sample centring motion
    # Using numbers to have the same order from ARINAX GUI
    sample__centring1_phi=device(
        "nicos_ess.nmx.devices.arinax.EpicsArinaxMoveable",
        description="ARINAX sample centring motor Phi (mockup)",
        readpv=f"{pv_root}getPhiPosition",
        writepv=f"{pv_root}setPhiPosition",
        unit="mm",
        pva=False,
    ),
    sample__centring2_chi=device(
        "nicos_ess.nmx.devices.arinax.EpicsArinaxMoveable",
        description="ARINAX sample centring motor Chi (mockup)",
        readpv=f"{pv_root}getChiPosition",
        writepv=f"{pv_root}setChiPosition",
        unit="mm",
        pva=False,
    ),
    sample__centring3_theta=device(
        "nicos_ess.nmx.devices.arinax.EpicsArinaxMoveable",
        description="ARINAX sample centring motor Theta (mockup)",
        readpv=f"{pv_root}getThetaPosition",
        writepv=f"{pv_root}setThetaPosition",
        unit="mm",
        pva=False,
    ),
    # Sample load
    sample__load_SS_sample=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedMoveable",
        description="ARINAX SPU load sample from storage, control (mockup)",
        readpv=f"{pv_root}LoadSSSample",
        writepv=f"{pv_root}LoadSSSample",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping=SAMPLE_STORAGE,
    ),
    sample__load_UP_sample=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedMoveable",
        description="ARINAX SPU load sample from unipucks, control (mockup)",
        readpv=f"{pv_root}LoadUPSample",
        writepv=f"{pv_root}LoadUPSample",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping=UNIPUCKS,

    ),
    # TODO: Issue here: mapping is broken. The PV is LONG type. Idea: Ask ARINAX to make them as ENUM.
    sample__sample_is_loaded=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="ARINAX SPU sample is mounted, readback (mockup)",
        readpv=f"{pv_root}getIsSampleLoaded",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        fmtstr="%.d",
        #mapping={
        #    'No': 0,
        #    'Yes': 1,
        #    },
    ),
    sample__unload_sample=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedMoveable",
        description="ARINAX SPU unload sample, control (mockup)",
        readpv=f"{pv_root}UnLoadSample",
        writepv=f"{pv_root}UnLoadSample",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping={
            'Unload sample': "1", # String PV. Preferably use "0" or "1".
            },
    ),
    # Sample tool
    tool__current_tool=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX SPU current mounted tool, readback (mockup)",
        readpv=f"{pv_root}getCurrentTool",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility=()
    ),
    tool__load_tool=device(
        "nicos_ess.nmx.devices.arinax.ConfigurableEpicsMappedMoveable",
        description="ARINAX SPU desired tool loading, control (mockup)",
        readpv=f"{pv_root}getCurrentTool",
        writepv=f"{pv_root}LoadTool",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        write_enum_string=True,
    ),

)
