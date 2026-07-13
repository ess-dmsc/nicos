description = "LoKI window guard"

devices = dict(
    window_guard=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Window guard - pneumatic axis 1 in motion cabinet 3",
        readpv="LOKI-WinGd1:MC-Pne-01:ShtAuxBits07",
        writepv="LOKI-WinGd1:MC-Pne-01:ShtOpen",
        statuspv="LOKI-WinGd1:MC-Pne-01:ShtStatusCode",
        resetpv="LOKI-WinGd1:MC-Pne-01:ShtErrRst",
        msgtxt="LOKI-WinGd1:MC-Pne-01:ShtMsgTxt",
    ),
)
