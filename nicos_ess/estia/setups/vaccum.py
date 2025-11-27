description = "ESTIA vacuum readouts"

inst_root = "ESTIA-VacInstr:Vac-"
bnkr_root = "ESTIA-VacBnkr:Vac-"


devices = dict(
    # Gate Valve
    gate_valve_1=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Instrument Vacuum gauge - the status of the gate valve interlock",
        readpv=f"{inst_root}VVS-100:StatR",
    ),
    gate_valve_1_open=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Instrument Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-100:OpenR",
    ),
    gate_valve_1_closed=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Instrument Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-100:ClosedR",
    ),
    gate_valve_2=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Instrument Vacuum gauge - the status of the gate valve interlock",
        readpv=f"{inst_root}VVS-200:StatR",
    ),
    gate_valve_2_open=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Instrument Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-200:OpenR",
    ),
    gate_valve_2_closed=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Instrument Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-200:ClosedR",
    ),
    gate_valve_3=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Instrument Vacuum gauge - the status of the gate valve interlock",
        readpv=f"{inst_root}VVS-300:StatR",
    ),
    gate_valve_3_open=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Instrument Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-300:OpenR",
    ),
    gate_valve_3_closed=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Instrument Vacuum valve - PLC",
        readpv=f"{inst_root}VVS-300:ClosedR",
    ),
    # Vacuum
    vacuum_11_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Instrument Vacuum 11 status",
        readpv=f"{inst_root}VPDP-011:StatR",
    ),
    vacuum_12_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Instrument Vacuum 12 status",
        readpv=f"{inst_root}VPDP-012:StatR",
    ),
    vacuum_21_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Instrument Vacuum 21 status",
        readpv=f"{inst_root}VPDP-021:StatR",
    ),
    vacuum_31_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Instrument Vacuum 31 status",
        readpv=f"{inst_root}VPDP-031:StatR",
    ),
    bnkr_vacuum_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Bunker Vacuum status",
        readpv=f"{bnkr_root}VPDP-011:StatR",
    ),
    # Pirani
    pirani_100=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Instrument Pirani 100 pressure",
        readpv=f"{inst_root}VGP-100:PrsR",
    ),
    pirani_200=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Instrument Pirani 200 pressure",
        readpv=f"{inst_root}VGP-200:PrsR",
    ),
    pirani_300=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Instrument Pirani 300 pressure",
        readpv=f"{inst_root}VGP-300:PrsR",
    ),
    bnkr_pirani_100=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Bunker Pirani 300 pressure",
        readpv=f"{bnkr_root}VGP-300:PrsR",
    ),
    bnkr_pirani_101=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Bunker Pirani 300 pressure",
        readpv=f"{bnkr_root}VGP-300:PrsR",
    ),
    bnkr_pirani_200=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Bunker Pirani 300 pressure",
        readpv=f"{bnkr_root}VGP-300:PrsR",
    ),
)
