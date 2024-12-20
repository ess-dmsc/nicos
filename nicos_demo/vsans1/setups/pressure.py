description = "Vacuum sensors of detector and collimation tube"

group = "lowlevel"

devices = dict(
    det_tube=device(
        "nicos.devices.generic.ManualMove",
        description="pressure detector tube: Tube",
        abslimits=(0, 1000),
        fmtstr="%.4G",
        pollinterval=15,
        maxage=60,
        visibility=(),
        unit="mbar",
        default=1e-8,
    ),
    det_nose=device(
        "nicos.devices.generic.ManualMove",
        description="pressure detector tube: Nose",
        abslimits=(0, 1000),
        fmtstr="%.4G",
        pollinterval=15,
        maxage=60,
        visibility=(),
        unit="mbar",
        default=1e-8,
    ),
    coll_tube=device(
        "nicos.devices.generic.ManualMove",
        description="pressure collimation tube: Tube",
        abslimits=(0, 1000),
        fmtstr="%.4G",
        pollinterval=15,
        maxage=60,
        visibility=(),
        unit="mbar",
        default=1e-8,
    ),
    coll_nose=device(
        "nicos.devices.generic.ManualMove",
        description="pressure collimation tube: Nose",
        abslimits=(0, 1000),
        fmtstr="%.4G",
        pollinterval=15,
        maxage=60,
        visibility=(),
        unit="mbar",
        default=1e-8,
    ),
    coll_pump=device(
        "nicos.devices.generic.ManualMove",
        description="pressure collimation tube: Pump",
        abslimits=(0, 1000),
        fmtstr="%.4G",
        pollinterval=15,
        maxage=60,
        visibility=(),
        unit="mbar",
        default=1e-8,
    ),
)
