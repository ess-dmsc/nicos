# ruff: noqa: F821
description = "A virtual motor"

devices = dict(
    virtual_motor=device(
        "nicos.devices.generic.VirtualMotor",
        description="Virtual linear axis",
        unit="mm",
        fmtstr="%.2f",
        abslimits=(-100, 100),
        speed=5,
    ),
)
