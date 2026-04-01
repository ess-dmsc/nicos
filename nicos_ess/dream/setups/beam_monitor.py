description = "The beam monitors setup file"

pv_root_1 = "DREAM-BM:NDet-FEN-001:"
pv_root_2 = "DREAM-BM:NDet-FEN-002:"

devices = dict(
    monitor_1=device(
        "nicos_ess.devices.epics.multiframe_histogrammer.MultiFrameHistogrammer",
        description="Consumes histograms from event-to-histogram converter",
        pv_root="DREAM:MFH-BM1:",
        readpv="DREAM:MFH-BM1:signal",
        source_name_input="cbm1",
        topic_input="dream_beam_monitor",
        pva=True,
        monitor=True,
        pollinterval=None,
    ),
    monitor_2=device(
        "nicos_ess.devices.epics.multiframe_histogrammer.MultiFrameHistogrammer",
        description="Consumes histograms from event-to-histogram converter",
        pv_root="DREAM:MFH-BM2:",
        readpv="DREAM:MFH-BM2:signal",
        source_name_input="cbm2",
        topic_input="dream_beam_monitor",
        pva=True,
        monitor=True,
        pollinterval=None,
    ),
    monitor1_high_voltage=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The value of the high voltage applied to the monitor 1",
        readpv=f"{pv_root_1}HighVoltage-R",
        writepv=f"{pv_root_1}HighVoltage-S",
        unit="V",
        abslimits=(0, 800),
    ),
    monitor1_high_voltage_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the high voltage of the monitor 1",
        readpv=f"{pv_root_1}HighVoltageStatus-R",
    ),
    monitor1_high_voltage_ramp=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="Ramp the high voltage of the monitor 1",
        readpv=f"{pv_root_1}HighVoltTask-S",
        writepv=f"{pv_root_1}HighVoltTask-S",
        mapping={"StartRamp": 1, "StopRamp": 0},
        unit="",
    ),
    monitor2_high_voltage=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high voltage of the monitor 2",
        readpv=f"{pv_root_2}HighVoltage-R",
        writepv=f"{pv_root_2}HighVoltage-S",
        unit="V",
        abslimits=(0, 800),
    ),
    monitor2_high_voltage_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The high voltage status of the monitor 2",
        readpv=f"{pv_root_2}HighVoltageStatus-R",
    ),
    monitor2_high_voltage_ramp=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="Ramp the high voltage value of the monitor 2",
        readpv=f"{pv_root_2}HighVoltTask-S",
        writepv=f"{pv_root_2}HighVoltTask-S",
        mapping={"StartRamp": 1, "StopRamp": 0},
        unit="",
    ),
)
