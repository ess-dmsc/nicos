description = "The temperature readout box for LOKI."

pv_root = "LOKI-SE:Proc-TIC-001:"

devices = dict()

num_cells = 8
for i in range(1, num_cells + 1):
    devices[f"temp_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"Temperature sensor {i}.",
        readpv=f"{pv_root}PT100_TS{i}",
    )
