description = "The UPS for the LoKI detector"

pv_root = "LOKI-Det:NDet-UPS-001:"

devices = dict(
    battery_status_int=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the battery",
        readpv="{}BatteryStatusInt-R".format(pv_root),
        mapping={"Unknown": 1, "Normal": 2, "Low": 3, "Depleted": 4},
        visibility=(),
    ),
    battery_status_str=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the battery",
        readpv="{}BatteryStatusStr-R".format(pv_root),
        visibility=(),
    ),
)
