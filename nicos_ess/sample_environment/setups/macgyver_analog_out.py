description = "The analog outputs of the MacGyver box."

group = "plugplay"

pv_root = "se-macgyver-001:"

extended = dict(
    presence_signal=f"pva://{pv_root}analog_out_1-R",
)

devices = dict()

for i in range(1, 5):
    devices[f"macgyver_analog_out_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description=f"MacGyver box analog out {i}",
        readpv=f"{pv_root}analog_out_{i}-R",
        writepv=f"{pv_root}analog_out_{i}-S",
        precision=0.0001,
    )
