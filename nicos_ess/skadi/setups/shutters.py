description = "SKADI shutters"

pv_root = "SKADI-HvSht:MC-Pne-01:"

devices = dict(
    safety_shutter=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Experiment shutter status",
        readpv=f"{pv_root}ShtAuxBits07",
    ),
)
