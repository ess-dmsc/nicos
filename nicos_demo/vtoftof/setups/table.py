description = "sample table and radial collimator"

group = "lowlevel"

devices = dict(
    gx=device(
        "nicos.devices.generic.VirtualMotor",
        description="X translation of the sample table",
        fmtstr="%7.3f",
        abslimits=(-20.0, 20.0),
        unit="mm",
        speed=1,
    ),
    gy=device(
        "nicos.devices.generic.VirtualMotor",
        description="Y translation of the sample table",
        fmtstr="%7.3f",
        abslimits=(-20.0, 20.0),
        unit="mm",
        speed=1,
    ),
    gz=device(
        "nicos.devices.generic.VirtualMotor",
        description="Z translation of the sample table",
        fmtstr="%7.3f",
        abslimits=(-14.8, 50.0),
        unit="mm",
        speed=1,
    ),
    gcx=device(
        "nicos.devices.generic.VirtualMotor",
        description="Chi rotation of the sample goniometer",
        fmtstr="%7.3f",
        abslimits=(-20.0, 20.0),
        unit="deg",
        speed=1,
    ),
    gcy=device(
        "nicos.devices.generic.VirtualMotor",
        description="Psi rotation of the sample goniometer",
        fmtstr="%7.3f",
        abslimits=(-20.0, 20.0),
        unit="deg",
        speed=1,
    ),
    gphi=device(
        "nicos.devices.generic.VirtualMotor",
        description="Phi rotation of the sample table",
        fmtstr="%7.3f",
        abslimits=(-20.0, 150.0),
        unit="deg",
        speed=1,
    ),
)
