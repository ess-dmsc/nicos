description = "The temperature inputs of the MacGyver box."

pv_root = "se-macgyver-001:"

devices = dict()

for i in range(1, 5):
    devices[f"macgyver_temperature_in_{i}"] = device(
        "nicos.devices.epics.pva.EpicsBoolReadable",
        description=f"MacGyver box temperature in {i}",
        readpv=f"{pv_root}thermo_{i}-R",
        nexus_config=[
            {
                "group_name": "macgyver_temperature",
                "nx_class": "NXcollection",
                "units": "K",
                "source_name": f"{pv_root}thermo_{i}-R",
                "schema": "f144",
                "topic": "ymir_motion",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    )
