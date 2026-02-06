description = "ARINAX sample motors (from the mockup software)"

group = "optional"

devices = dict(
    phi=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample motor Phi (mockup)",
        readpv="NMX:PhiPosition",
        writepv="NMX:PhiPosition",
        unit="mm",
        pva=False,
    ),
    # The rest of the sample (SPU) motors  to be added here, once they are available. 
    dpu_config_str_read=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="ARINAX DPU Configuration (mockup)",
        readpv="NMX:DPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    dpu_config_str_move=device(
        "nicos_ess.devices.epics.pva.EpicsStringMoveable",
        description="ARINAX DPU Configuration (mockup)",
        readpv="NMX:DPUConfiguration",
        writepv="NMX:putDPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    dpu_config_map_read=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="ARINAX DPU Configuration (mockup)",
        readpv="NMX:DPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    dpu_config_map_move=device(
        # This class seems to be the best for read/write the DPU config PV.
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="ARINAX DPU Configuration (mockup)",
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
    dpu_config_dig_move=device(
        "nicos_ess.devices.epics.pva.EpicsDigitalMoveable",
        description="ARINAX DPU Configuration (mockup)",
        readpv="NMX:DPUConfiguration",
        writepv="NMX:putDPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),

)
