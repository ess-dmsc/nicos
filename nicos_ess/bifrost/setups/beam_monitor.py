description = "The monitor detector."

devices = dict(
    monitor_1=device(
        "nicos_ess.devices.epics.multiframe_histogrammer.MultiFrameHistogrammer",
        description="Multi-frame histogrammer",
        pv_root="BIFR:MFHist:",
        readpv="BIFR:MFHist:signal",
        pva=True,
        monitor=True,
        pollinterval=None,
    ),
    bunker_cbm_sampling_period=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The sampling period of the monitor detector",
        readpv="BIFRO-BM1:NDet-CDTIBM-001:SamplingPeriod-R",
        writepv="BIFRO-BM1:NDet-CDTIBM-001:SamplingPeriod-S",
        unit="us",
        abslimits=(1.2, 132.3),
    ),
    bunker_cbm_high_voltage=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high voltage of the monitor detector",
        readpv="BIFRO-BM1:NDet-CDTIBM-001:HighVoltage-R",
        writepv="BIFRO-BM1:NDet-CDTIBM-001:HighVoltage-S",
        unit="V",
        abslimits=(0, 800),
    ),
    bunker_cbm_high_voltage_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The high voltage status of the monitor detector",
        readpv="BIFRO-BM1:NDet-CDTIBM-001:HighVoltageStatus-R",
    ),
    chopper_cbm_sampling_period=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The sampling period of the monitor detector",
        readpv="BIFRO-BM1:NDet-CDTIBM-002:SamplingPeriod-R",
        writepv="BIFRO-BM1:NDet-CDTIBM-002:SamplingPeriod-S",
        unit="us",
        abslimits=(1.2, 132.3),
    ),
    chopper_cbm_high_voltage=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high voltage of the monitor detector",
        readpv="BIFRO-BM1:NDet-CDTIBM-002:HighVoltage-R",
        writepv="BIFRO-BM1:NDet-CDTIBM-002:HighVoltage-S",
        unit="V",
        abslimits=(0, 800),
    ),
    chopper_cbm_high_voltage_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The high voltage status of the monitor detector",
        readpv="BIFRO-BM1:NDet-CDTIBM-002:HighVoltageStatus-R",
    ),
)
