description = "The UPS for the LoKI detector"

pv_root = "LOKI-Det:NDet-UPS-001:"

devices = dict(
    battery_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the battery",
        readpv="{}BatteryStatusInt-R".format(pv_root),
    )
)
