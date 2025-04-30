description = "LoKI heavy shutter"

pv_root = "LOKI-HvSht:MC-Pne-01:"

### IN PROGRESS!!

devices = dict(
    heavy_shutter=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Heavy shutter - pneumatic axis 1 in motion cabinet 1",
        readpv=f"{pv_root}ShtAuxBits07",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    heavy_shutter_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the heavy shutter",
        readpv=f"{pv_root}ShtMsgTxt",
    ),
    heavy_shutter_error=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Error status of the heavy shutter",
        readpv=f"{pv_root}ShtErr",
    ),
)
