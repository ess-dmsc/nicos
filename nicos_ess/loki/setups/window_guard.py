description = "LoKI window guard"

devices = dict(
    window_guard=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Window guard - pneumatic axis 1 in motion cabinet 3",
        readpv="LOKI-WinGd1:MC-Pne-01:ShtAuxBits07",
        writepv="LOKI-WinGd1:MC-Pne-01:ShtOpen",
        resetpv="LOKI-WinGd1:MC-Pne-01:ShtErrRst",
    ),
    window_guard_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the window guard",
        readpv="LOKI-WinGd1:MC-Pne-01:ShtMsgTxt",
    ),
)
