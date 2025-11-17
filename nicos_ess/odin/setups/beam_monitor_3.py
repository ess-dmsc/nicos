description = "The monitor detector."

devices = dict(
    monitor_1=device(
        "nicos_ess.devices.epics.multiframe_histogrammer.MultiFrameHistogrammer",
        description="Multi-frame histogrammer",
        pv_root="ODIN:MFHist-003:",
        readpv="ODIN:MFHist-003:signal",
        pva=True,
        monitor=True,
        pollinterval=None,
    ),
    monitor_1_high_voltage=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high voltage of the monitor detector",
        readpv="ODIN-BM:NDet-CDTIBM-003:HighVoltage-R",
        writepv="ODIN-BM:NDet-CDTIBM-003:HighVoltage-S",
        unit="V",
        abslimits=(0, 800),
    ),
    monitor_1_high_voltage_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The high voltage status of the monitor detector",
        readpv="ODIN-BM:NDet-CDTIBM-003:HighVoltageStatus-R",
    ),
    monitor_1_high_voltage_start_ramp=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="Start ramping the high voltage of the monitor",
        readpv="ODIN-BM:NDet-CDTIBM-003:HighVoltTask-S",
        writepv="ODIN-BM:NDet-CDTIBM-003:HighVoltTask-S",
        mapping={"StartRamp": 1, "StopRamp": 0},
        unit="",
    ),
)
