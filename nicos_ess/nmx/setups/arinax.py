description = "ARINAX sample motors (from the mockup software)"

group = "optional"

devices = dict(
    # Sample motion
    phi=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample motor Phi (mockup)",
        readpv="NMX:PhiPosition",
        writepv="NMX:PhiPosition",
        unit="mm",
        pva=False,
    ),
    # DPU Config
    DPU_config_readback=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX DPU Configuration readback (mockup)",
        readpv="NMX:DPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    DPU_config_control=device(
        # This class seems to be the best for read/write the DPU config PV.
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="ARINAX DPU Configuration control (mockup)",
        readpv="NMX:DPUConfiguration",
        writepv="NMX:putDPUConfiguration",
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

)
