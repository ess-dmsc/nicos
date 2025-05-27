description = "The monitor detector."

devices = dict(
    monitor_1=device(
        "nicos_ess.devices.epics.multiframe_histogrammer.MultiFrameHistogrammer",
        description="Multi-frame histogrammer",
        pv_root="TBL:MFHist:",
        readpv="TBL:MFHist:signal",
        pva=True,
        monitor=True,
        pollinterval=None,
    ),
    monitor_sampling_period=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The sampling period of the monitor detector",
        readpv="TBL-BM:NDet-CDTIBM-001:SamplingPeriod-R",
        writepv="TBL-BM:NDet-CDTIBM-001:SamplingPeriod-S",
        unit="us",
        abslimits=(1.2, 132.3),
    ),
    monitor_high_voltage=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high voltage of the monitor detector",
        readpv="TBL-BM:NDet-CDTIBM-001:HighVoltage-R",
        writepv="TBL-BM:NDet-CDTIBM-001:HighVoltage-S",
        unit="V",
        abslimits=(0, 800),
    ),
    monitor_high_voltage_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The high voltage status of the monitor detector",
        readpv="TBL-BM:NDet-CDTIBM-001:HighVoltageStatus-R",
    ),
)
