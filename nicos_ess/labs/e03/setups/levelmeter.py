description = "LHe/LN2 Levelmeter AMI1700"

pv_root = "SE-SEE:SE-AMILVL-001:"

devices = dict(
    levelmeter_N2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Liquid nitrogen level",
        readpv=f"{pv_root}N2Monitor",
    ),
    levelmeter_He=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Liquid helium level",
        readpv=f"{pv_root}HeMonitor",
    ),
)
