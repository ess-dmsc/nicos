description = "The monitor detector."

pv_root = "ODIN-BM:NDet-FEN-002:"

devices = dict(
    monitor_2=device(
        "nicos_ess.devices.epics.multiframe_histogrammer.MultiFrameHistogrammer",
        description="Multi-frame histogrammer",
        pv_root="ODIN:MFHist-002:",
        readpv="ODIN:MFHist-002:signal",
        pva=True,
        monitor=True,
        pollinterval=None,
    ),
    monitor_2_high_voltage=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high voltage of the monitor detector",
        readpv=f"{pv_root}HighVoltage-R",
        writepv=f"{pv_root}HighVoltage-S",
        unit="V",
        abslimits=(0, 800),
    ),
    monitor_2_high_voltage_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The high voltage status of the monitor detector",
        readpv=f"{pv_root}HighVoltageStatus-R",
    ),
    monitor_2_high_voltage_start_ramp=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="Start ramping the high voltage of the monitor",
        readpv=f"{pv_root}HighVoltTask-S",
        writepv=f"{pv_root}HighVoltTask-S",
        mapping={"StartRamp": 1, "StopRamp": 0},
        unit="",
    ),
)
