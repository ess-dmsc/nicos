description = "The monitor detector."

pv_root = "TBL-BM:NDet-FEN-002:"

devices = dict(
    monitor_high_voltage=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high voltage of the monitor detector",
        readpv=f"{pv_root}HighVoltage-R",
        writepv=f"{pv_root}HighVoltage-S",
        unit="V",
        abslimits=(0, 800),
        precision=100.0,  # The readback of the high voltage has a lot of error, 100V should be safe
    ),
    monitor_high_voltage_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The high voltage status of the monitor detector",
        readpv=f"{pv_root}HighVoltageStatus-R",
    ),
    monitor_high_voltage_start_ramp=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="Start ramping the high voltage of the monitor",
        readpv=f"{pv_root}HighVoltTask-S",
        writepv=f"{pv_root}HighVoltTask-S",
        mapping={"StartRamp": 1, "StopRamp": 0},
        unit="",
    ),
)
