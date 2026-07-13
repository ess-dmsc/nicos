description = "LOKI vacuum readouts (gauges and valves)"

devices = dict(
    vacuum_gauge=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Vacuum gauge - MicroPirani sensor pressure (PR1), MKS910 IOC",
        readpv="LOKI-VacInstr:Vac-VGF-050:PR3-R",
        fmtstr="%.6f",
    ),
    gate_valve_interlock=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum gauge - the status of the gate valve interlock",
        readpv="LOKI-VacInstr:Vac-VVS-400:IntlckLED",
    ),
    gate_valve=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum valve - the state of the gate valve",
        readpv="LOKI-VacInstr:Vac-VVS-400:StatR",
    ),
)
