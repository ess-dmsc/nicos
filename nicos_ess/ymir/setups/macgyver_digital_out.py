description = "The digital outputs of the MacGyver box."

pv_root = "se-macgyver-001:"

devices = dict()

for i in range(1, 9):
    devices[f"macgyver_digital_out_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description=f"MacGyver box digital out {i}",
        readpv=f"{pv_root}digital_out_{i}-R",
        writepv=f"{pv_root}digital_out_{i}-S",
    )
