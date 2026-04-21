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
    arinax_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX System Status (mockup)",
        readpv="NMX-mockup:getStatus",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    arinax_state=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX System State (mockup)",
        readpv="NMX-mockup:getState",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    # DPU Config
    detector_config_readback=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX DPU Configuration, readback (mockup)",
        readpv="NMX-mockup:getDPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    detector_config_setpoint=device(
        # Just for testing, coudl be removed later.
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="ARINAX DPU Configuration, setpoint readback (mockup)",
        readpv="NMX-mockup:getDPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    detector_config_control=device(
        # Showing only the index!
        # This class seems to be the best so far for read/write the DPU config PV.
        # PS: This PV is being fixed. Probably it will be an ENUM too in the future.
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="ARINAX DPU Configuration, control (mockup)",
        readpv="NMX-mockup:getDPUConfiguration",
        writepv="NMX-mockup:setDPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        # Add mapping here to override the one from readpv (ENUM), as the writepv is a STRING.
        mapping={
            'PARK': "PARK",
            'CALIBRATION': "CALIBRATION",
            'MAINTENANCE': "MAINTENANCE",
            'CONFIG1':"CONFIG1",
            'CONFIG2':"CONFIG2", 
            'CONFIG3':"CONFIG3", 
            'CONFIG4':"CONFIG4", 
            'CONFIG5':"CONFIG5",
            'CONFIG6':"CONFIG6",
            'CONFIG7':"CONFIG7",
            'CONFIG8':"CONFIG8",
            'CONFIG9':"CONFIG9",
            'CONFIG10':"CONFIG10",
            'CONFIG11':"CONFIG11",
            }
    ),
    # Sample centring motion
    sample_centring_phi=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample motor Phi (mockup)",
        readpv="NMX-mockup:getPhiPosition",
        writepv="NMX-mockup:setPhiPosition", # String type, incompatible here.
        unit="mm",
        pva=False,
    ),
    sample_centring_chi=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample motor Chi (mockup)",
        readpv="NMX-mockup:getChiPosition",
        writepv="NMX-mockup:setChiPosition",
        unit="mm",
        pva=False,
    ),
    sample_centring_theta=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample motor Theta (mockup)",
        readpv="NMX-mockup:getThetaPosition",
        writepv="NMX-mockup:setThetaPosition",
        unit="mm",
        pva=False,
    ),
    # Sample tool
    sample_tool__load_tool=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="ARINAX SPU desired tool loading, control (mockup)",
        readpv="NMX-mockup:LoadTool",
        writepv="NMX-mockup:LoadTool",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping={
            "GoniometerEmpty": "GoniometerEmpty",
            "CustomToolEmpty": "CustomToolEmpty",
            "TouchProbe": "TouchProbe",
            "ToolChanger": "ToolChanger",
            "GoniometerSample": "GoniometerSample",
            "CustomToolSample": "CustomToolSample",
            "None": "None",
        },
    ),
    sample_tool__current_tool=device(
        # Only index is showing.
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX SPU current mounted tool, readback (mockup)",
        readpv="NMX-mockup:getCurrentTool",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping={
            'No': 0,
            'Yes': 1,
            },
    ),
    # Sample load
    sample_load__sample_is_loaded=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX SPU sample is mounted, readback (mockup)",
        readpv="NMX-mockup:getIsSampleLoaded",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping={
            'No': 0,
            'Yes': 1,
            },
    ),
    sample_load__load_SS_sample=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
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
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="ARINAX SPU load sample from unipucks, control (mockup)",
        readpv="NMX-mockup:LoadUPSample",
        writepv="NMX-mockup:LoadUPSample",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        mapping=UNIPUCKS,
    ),
    sample_load__unload_sample=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
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

)
