description = "The monitor detector."

devices = dict(
    monitor_high_voltage=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high voltage of the monitor detector",
        readpv="TBL-BM:NDet-CDTIBM-001:HighVoltage-R",
        writepv="TBL-BM:NDet-CDTIBM-001:HighVoltage-S",
        unit="V",
        abslimits=(0, 800),
        precision=100.0,  # The readback of the high voltage has a lot of error, 100V should be safe
    ),
    monitor_high_voltage_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The high voltage status of the monitor detector",
        readpv="TBL-BM:NDet-CDTIBM-001:HighVoltageStatus-R",
    ),
    monitor_high_voltage_start_ramp=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="Start ramping the high voltage of the monitor",
        readpv="TBL-BM:NDet-CDTIBM-001:HighVoltTask-S",
        writepv="TBL-BM:NDet-CDTIBM-001:HighVoltTask-S",
        mapping={"StartRamp": 1, "StopRamp": 0},
        unit="",
    ),
)
