description = "Monitoring for the Beryllium filter"

pv_prefix = "BIFRO-Det:Proc-TIC-001:"
pv_channel_prefix = f"{pv_prefix}PT100_CH"

devices = {
    "average_beryllium_filter_temperature": device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Average temperature of channel 1, 3, 4, 8 and 9. Used to monitor filter temperature alarm.",
        readpv=f"{pv_prefix}AvgFilterTemp",
    ),
}

for i in range(1, 15):
    desc = f"Temperature of PT100 channel {i}."
    if i in [10, 13]:
        desc += " Alarm state when filling is needed."
    devices[f"beryllium_filter_T{i:02d}"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=desc,
        readpv=f"{pv_channel_prefix}{i:02d}",
    )
