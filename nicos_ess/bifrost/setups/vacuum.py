description = "Vacuum status for BIFROST"

BUNKER_ROOT = "BIFRO-VacBnkr:Vac-"
INSTRUMENT_ROOT = "BIFRO-VacInstr:Vac-"

BUNKER_GAUGES = [
    "VGP-100",
    "VGP-011",
    "VGP-021",
    "VGP-200",
    "VGP-201",
    "VGP-300",
    "VGP-031",
    "VGP-400",
    "VGP-301",
    "VGP-022",
    "VGP-012",
    "VGC-012",
]

INSTRUMENT_GAUGES = [
    "VGP-011",
    "VGP-012",
    "VGP-100",
    "VGP-200",
    "VGP-021",
    "VGP-022",
    "VGP-031",
    "VGP-041",
    "VGP-300",
]


def make_key(zone: str, tag: str) -> str:
    return f"{zone}_vacuum_{tag.lower().replace('-', '')}"


# Commenting out code = bad practice - but I'll do it here in case they want all these signals again
# devices = {}
# for zone, root, tags in [
#     ("bunker", BUNKER_ROOT, BUNKER_GAUGES),
#     ("instrument", INSTRUMENT_ROOT, INSTRUMENT_GAUGES),
# ]:
#     for tag in tags:
#         devices[make_key(zone, tag)] = device(
#             "nicos_ess.devices.epics.pva.EpicsReadable",
#             description=f"{zone.capitalize()} zone vacuum gauge {tag.split('-')[-1]}",
#             readpv=f"{root}{tag}:PrsR",
#         )


devices = dict(
    tank_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Instrument zone tank vacuum pressure",
        readpv="BIFRO-VacInstr:Vac-VGP-031:PrsR",
        fmtstr="%.2e",
    ),
    be_filter_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Instrument zone Be filter vacuum pressure",
        readpv="BIFRO-VacInstr:Vac-VGF-032:PrsR",
        fmtstr="%.2e",
    ),
    be_filter_pressure_ok=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Instrument zone Be filter vacuum pressure OK status. set is OK",
        readpv="BIFRO-VacInstr:Vac-VGF-032:Rly2Stat-R",
    ),
    backing_pump_interlock=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Instrument zone Be filter valve interlock status. HEALTHY is OK",
        readpv="BIFRO-VacInstr:Vac-VVA-032:ITLckStatR",
    ),
)
