description = "The solid-state relays of the MacGyver box."

pv_root = "se-macgyver-001:"

devices = dict()

for i in range(1, 5):
    devices[f"macgyver_relay_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description=f"MacGyver box relay {i}",
        readpv=f"{pv_root}relay_{i}-R",
        writepv=f"{pv_root}relay_{i}-S",
    )
