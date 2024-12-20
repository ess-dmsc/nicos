description = "chopper vacuum readout"

group = "lowlevel"

devices = dict(
    vac0=device(
        "nicos.devices.generic.ManualMove",
        description="Vacuum sensor in chopper vessel 1",
        default=1.7e-6,
        abslimits=(0, 1000),
        pollinterval=10,
        maxage=12,
        unit="mbar",
        fmtstr="%.1g",
    ),
    vac1=device(
        "nicos.devices.generic.ManualMove",
        description="Vacuum sensor in chopper vessel 2",
        default=0.00012,
        abslimits=(0, 1000),
        pollinterval=10,
        maxage=12,
        unit="mbar",
        fmtstr="%.1g",
    ),
    vac2=device(
        "nicos.devices.generic.ManualMove",
        description="Vacuum sensor in chopper vessel 3",
        default=3.5e-6,
        abslimits=(0, 1000),
        pollinterval=10,
        maxage=12,
        unit="mbar",
        fmtstr="%.1g",
    ),
    vac3=device(
        "nicos.devices.generic.ManualMove",
        description="Vacuum sensor in chopper vessel 4",
        default=5.0e-6,
        abslimits=(0, 1000),
        pollinterval=10,
        maxage=12,
        unit="mbar",
        fmtstr="%.1g",
    ),
)
