description = "LOKI vacuum readouts (gauges and valves)"

devices = dict(
    sample_area_vacuum_gauge=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Vacuum gauge - MicroPirani sensor pressure (PR1), MKS910 IOC",
        readpv="LOKI-VacInstr:Vac-VGF-050:PR3-R",
        fmtstr="%.6f",
        visiblitity=(),
    ),
    sample_area_vacuum_gate_valve_interlock=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Vacuum gauge - the status of the gate valve interlock",
        readpv="LOKI-VacInstr:Vac-VVS-400:IntlckLED",
        visiblitity=(),
    ),
    sample_area_vacuum_valve_open=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum valve - PLC",
        readpv="LOKI-VacInstr:Vac-VVS-400:OpenR",
        visiblitity=(),
    ),
    sample_area_vacuum_valve_closed=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum valve - PLC",
        readpv="LOKI-VacInstr:Vac-VVS-400:ClosedR",
        visiblitity=(),
    ),
)
