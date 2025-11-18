description = "ESTIA vacuum readouts (gauges and valves)"

inst_root = "ESTIA-VacInstr:Vac-"


devices = dict(
    gate_valve_1=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum gauge - the status of the gate valve interlock",
        readpv=f"{inst_root}VVS-100:IntlckLED",
        visiblitity=(),
    ),
    gate_valve_1_open=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-100:OpenR",
        visiblitity=(),
    ),
    gate_valve_1_closed=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-100:ClosedR",
        visiblitity=(),
    ),
    gate_valve_2=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum gauge - the status of the gate valve interlock",
        readpv=f"{inst_root}VVS-200:IntlckLED",
        visiblitity=(),
    ),
    gate_valve_2_open=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-200:OpenR",
        visiblitity=(),
    ),
    gate_valve_2_closed=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-200:ClosedR",
        visiblitity=(),
    ),
    gate_valve_3=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum gauge - the status of the gate valve interlock",
        readpv=f"{inst_root}VVS-300:IntlckLED",
        visiblitity=(),
    ),
    gate_valve_3_open=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-300:OpenR",
        visiblitity=(),
    ),
    gate_valve_3_closed=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-300:ClosedR",
        visiblitity=(),
    ),
)
