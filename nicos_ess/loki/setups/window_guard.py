description = "LoKI detector tank window guard"

pv_root = "WinGd1:MC-Pne-01:"

devices = dict(
    window_guard=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Detector tank window guard - pneumatic axis 1 in motion cabinet 3",
        readpv=f"{pv_root}ShtAuxBits07",
        writepv=f"{pv_root}ShtOpen",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
)
