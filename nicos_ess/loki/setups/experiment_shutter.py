description = "LoKI experiment shutter"

pv_root = "LOKI-ExSh:MC-Pne-01:"

devices = dict(
    experiment_shutter_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Experiment shutter - pneumatic axis 2 in motion cabinet 3",
        readpv=f"{pv_root}ShtAuxBits07",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    experiment_shutter=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Experiment shutter - pneumatic axis 2 in motion cabinet 3",
        readpv=f"{pv_root}ShtOpen",
        writepv=f"{pv_root}ShtOpen",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
)
