description = "LoKI window guard"

devices = dict(
    window_guard=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Heavy shutter - pneumatic axis 1 in motion cabinet 3",
        readpv="LOKI-WinGd1:MC-Pne-01:ShtAuxBits07",
    ),
)
