description = "ARINAX sample motors (from the mockup software)"

group = "basic"

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
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="ARINAX DPU Configuration (mockup)",
        readpv="NMX:DPUConfiguration",
        writepv="NMX:putDPUConfiguration",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
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
