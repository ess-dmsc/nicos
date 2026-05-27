description = "ARINAX controls (from the mockup software)"

group = "optional"

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
        readpv="NMX-mockup:getState",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    arinax_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="ARINAX System Status (mockup)",
        readpv="NMX-mockup:getStatus",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    # DPU Config
    detector_config_control=device(
        "nicos_ess.nmx.devices.arinax.ConfigurableEpicsMappedMoveable",
        description="ARINAX DPU Configuration, control (mockup)",
        readpv="NMX-mockup:getDPUConfiguration",
        writepv="NMX-mockup:setDPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        write_enum_string=True,
    ),
    detector_config_readback=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX DPU Configuration, readback (mockup)",
        readpv="NMX-mockup:getDPUConfiguration",
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
        readpv="NMX-mockup:setDPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility=(),
    ),
    # Sample centring motion
    sample_centring_chi=device(
        "nicos_ess.nmx.devices.arinax.EpicsArinaxMoveable",
        description="ARINAX sample motor Chi (mockup)",
        readpv="NMX-mockup:getChiPosition",
        writepv="NMX-mockup:setChiPosition",
        unit="mm",
        pva=False,
    ),
    sample_centring_phi=device(
        "nicos_ess.nmx.devices.arinax.EpicsArinaxMoveable",
        description="ARINAX sample motor Phi (mockup)",
        readpv="NMX-mockup:getPhiPosition",
        writepv="NMX-mockup:setPhiPosition",
        unit="mm",
        pva=False,
    ),
    sample_centring_theta=device(
        "nicos_ess.nmx.devices.arinax.EpicsArinaxMoveable",
        description="ARINAX sample motor Theta (mockup)",
        readpv="NMX-mockup:getThetaPosition",
        writepv="NMX-mockup:setThetaPosition",
        unit="mm",
        pva=False,
    ),
    # Sample load
    sample_load__load_SS_sample=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedMoveable",
        description="ARINAX SPU load sample from storage, control (mockup)",
        readpv="NMX-mockup:LoadSSSample",
        writepv="NMX-mockup:LoadSSSample",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping=SAMPLE_STORAGE,
    ),
    sample_load__load_UP_sample=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedMoveable",
        description="ARINAX SPU load sample from unipucks, control (mockup)",
        readpv="NMX-mockup:LoadUPSample",
        writepv="NMX-mockup:LoadUPSample",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping=UNIPUCKS,

    ),
    # TODO: Issue here: mapping is broken. The PV is LONG type. Idea: Ask ARINAX to make them as ENUM.
    sample_load__sample_is_loaded=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="ARINAX SPU sample is mounted, readback (mockup)",
        readpv="NMX-mockup:getIsSampleLoaded",
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
    sample_load__unload_sample=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedMoveable",
        description="ARINAX SPU unload sample, control (mockup)",
        readpv="NMX-mockup:UnLoadSample",
        writepv="NMX-mockup:UnLoadSample",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping={
            'Unload sample': "1", # Any string should be okay.
            },
    ),
    # Sample tool
    tool__current_tool=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX SPU current mounted tool, readback (mockup)",
        readpv="NMX-mockup:getCurrentTool",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility=()
    ),
    tool__load_tool=device(
        "nicos_ess.nmx.devices.arinax.ConfigurableEpicsMappedMoveable",
        description="ARINAX SPU desired tool loading, control (mockup)",
        readpv="NMX-mockup:getCurrentTool",
        writepv="NMX-mockup:LoadTool",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        write_enum_string=True,
    ),

)
