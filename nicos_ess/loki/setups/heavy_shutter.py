description = "LoKI heavy shutter"

pv_root = "LOKI-HvSht:MC-Pne-01:"

devices = dict(
    heavy_shutter=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Heavy shutter - pneumatic axis 1 in motion cabinet 1",
        readpv=f"{pv_root}ShtMsgTxt",
    ),
    heavy_shutter_error=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Error status of the heavy shutter",
        readpv=f"{pv_root}ShtErr",
    ),
)
