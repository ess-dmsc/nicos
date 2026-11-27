description = "Presence of plug-and-play sample environment equipment"

group = "lowlevel"

devices = dict(
    se_presence=device(
        "nicos_ess.devices.sample_environment.SampleEnvironmentPresence",
        description="Plug-and-play setups whose equipment is present",
        visibility=(),
    ),
)
