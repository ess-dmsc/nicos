description = "The UPS for the LoKI detector"

pv_root = "LOKI-Det:NDet-UPS-001:"

devices = dict(
    battery_status=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="1=Unknown; 2=Normal; 3=Low; 4=Depleted.",
        readpv="{}BatteryStatusInt-R".format(pv_root),
        visibility=(),
    )
)
