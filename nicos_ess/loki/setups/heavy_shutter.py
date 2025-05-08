description = "LoKI heavy shutter"

pv_root = "LOKI-HvSht:MC-Pne-01:"

devices = dict(
    heavy_shutter=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Heavy shutter - pneumatic axis 1 in motion cabinet 1",
        readpv=f"{pv_root}ShtAuxBits07",
    ),
)
