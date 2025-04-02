description = "The UPS for the LoKI detector"

pv_root = "LOKI-Det:NDet-UPS-001:"

devices = dict(
    battery_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the battery",
        readpv="{}BatteryStatusStr-R".format(pv_root),
        visibility=(),
    ),
    output_source=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Present source of output power in string. None mean no output at all.",
        readpv="{}OutputSourceStr-R".format(pv_root),
        visibility=(),
    ),
)
