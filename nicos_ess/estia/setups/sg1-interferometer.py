description = "Prototype interferometer measurement"

etalon_prefix = "ESTIA-Sel1:Mech-GU-001"

# group = "lowlevel"

devices = dict(
    multiline1=device(
        "nicos_ess.estia.devices.multiline.MultilineController",
        description="Multiline interferometer controller",
        pvprefix=etalon_prefix,
        readpv=f"{etalon_prefix}:MeasState-R",
        epicstimeout=30.0,
        # pilot_laser='pilot_laser',
        # temperature='env_temperature',
        # pressure='env_pressure',
        # humidity='env_humidity'
    ),
)

channels = [1, 2, 3, 4, 5, 6, 7, 8, 11, 12]

for ch in channels:
    devices[f"ch{ch:02}"] = device(
        "nicos_ess.estia.devices.multiline.MultilineChannel",
        description=f"Value of channel {ch}",
        channel=ch,
        controller="multiline1",
        unit="mm",
    )
