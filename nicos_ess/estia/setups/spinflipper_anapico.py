description = "Keysight AnaPico Sin2010 - Spinflipper"

pv_root = "ESTIA:RF-SG-001:"


devices = dict(
    frequency=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Signal frequency",
        readpv="ESTIA:RF-SG-001:Freq-R",
        writepv="ESTIA:RF-SG-001:Freq-S",
    ),
    power=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Signal power",
        readpv="ESTIA:RF-SG-001:Power-R",
        writepv="ESTIA:RF-SG-001:Power-S",
    ),
    output_switch=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Switch output signal on and off",
        readpv="ESTIA:RF-SG-001:PulseEn-R",
        writepv="ESTIA:RF-SG-001:PulseEn-S",
    ),
)
