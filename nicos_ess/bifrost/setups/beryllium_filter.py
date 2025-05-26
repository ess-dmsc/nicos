description = "Monitoring for the Beryllium filter"

pv_prefix = "BIFRO-Det:Proc-TIC-001:PT100_CH"

devices = {}

for i in range(1, 15):
    devices[f"beryllium_filter_T{i:02d}"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"Temperature of PT100 channel {i}",
        readpv=f"{pv_prefix}{i:02d}",
    )
