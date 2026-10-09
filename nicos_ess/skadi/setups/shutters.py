description = "SKADI shutters"

pv_root = "SKADI-"

devices = dict(
    heavy_shutter=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Instrument Safety Shutter 1 (Heavy) status",
        readpv=f"{pv_root}HvSht:MC-Pne-01:ShtAuxBits07",
    ),
    light_shutter=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Instrument Safety Shutter 2 (Thermal) status",
        readpv=f"{pv_root}ThSht:MC-Pne-01:ShtAuxBits07",
    ),
)
