# ruff: noqa: F821
description = "The temperature inputs of the MacGyver box."

group = "plugplay"

pv_root = "se-macgyver-001:"
sample_env_topic = configdata("config.SAMPLE_ENV_TOPIC")

extended = dict(
    presence_signal=f"pva://{pv_root}thermo_1-R",
)

devices = dict()

for i in range(1, 5):
    devices[f"macgyver_temperature_in_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"MacGyver box temperature in {i}",
        readpv=f"{pv_root}thermo_{i}-R",
        nexus_config=[
            {
                "group_name": "macgyver_temperature",
                "nx_class": "NXcollection",
                "units": "K",
                "suffix": "readback",
                "source_name": f"{pv_root}thermo_{i}-R",
                "topic": sample_env_topic,
                "schema": "f144",
                "dataset_type": "nx_log",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
    )
