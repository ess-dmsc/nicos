description = "The digital inputs of the MacGyver box."

group = "plugplay"

pv_root = "se-macgyver-001:"

extended = dict(
    presence_signal=f"pva://{pv_root}digital_in_1-R",
)

devices = dict()

for i in range(1, 9):
    devices[f"macgyver_digital_in_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description=f"MacGyver box digital in {i}",
        readpv=f"{pv_root}digital_in_{i}-R",
    )
