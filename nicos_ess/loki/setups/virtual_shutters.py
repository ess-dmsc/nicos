description = "Instrument shutter"

devices = dict(
    virtual_fast_shutter=device(
        "nicos.devices.generic.ManualSwitch",
        description="Shutter just before the sample",
        states=["Open", "Closed"],
    ),
    virtual_heavy_shutter=device(
        "nicos.devices.generic.ManualSwitch",
        description="Main shutter",
        states=["Open", "Closed"],
    ),
)
