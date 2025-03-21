description = "Shutters"

devices = dict(
    aperture_x=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Light shutter",
        abslimits=(0, 100),
        userlimits=(0, 100),
        fmtstr="%.f",
        unit="mm",
        speed=5,
        requires={"level": "admin"},
    ),
    aperture_y=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Heavy shutter",
        abslimits=(0, 100),
        userlimits=(0, 100),
        fmtstr="%.f",
        unit="mm",
        speed=5,
        requires={"level": "admin"},
    ),
)
