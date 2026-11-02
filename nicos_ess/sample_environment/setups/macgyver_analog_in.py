description = "The analog inputs of the MacGyver box."

group = "plugplay"

pv_root = "se-macgyver-001:"

extended = dict(
    presence_signal=f"pva://{pv_root}analog_in_1-R",
)

devices = dict()

for i in range(1, 5):
    devices[f"macgyver_analog_in_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description=f"MacGyver box analog in {i}",
        readpv=f"{pv_root}analog_in_{i}-R",
    )
