description = "LOKI vacuum readouts (gauges and valves)"

devices = dict(
    sample_area_vacuum_gauge=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Vacuum gauge - MicroPirani sensor pressure (PR1), MKS910 IOC",
        readpv="LOKI-VacInstr:Vac-VGF-050:PR3-R",
        fmtstr="%.6f",
        visiblitity=(),
    ),
    sample_area_vacuum_valve=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum valve - PLC",
        readpv="LOKI-VacInstr:Vac-VVS-400:OpenR",
        visiblitity=(),
    ),
)
