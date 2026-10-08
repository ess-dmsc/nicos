description = "SKADI shutters"

pv_root = "SKADI-"

devices = dict(
    safety_shutter_1=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Safety shutter 1 (heavy) status",
        readpv=f"{pv_root}HvSht:MC-Pne-01:ShtAuxBits07",
    ),
    safety_shutter_2=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Safety shutter 2 (thermal) status",
        readpv=f"{pv_root}ThSht:MC-Pne-01:ShtAuxBits07",
    ),
)
