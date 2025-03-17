description = "Virtual motors (for testing/debugging)"

group = "optional"

devices = dict(
    virtual_motor_1=device(
        "nicos.devices.generic.VirtualMotor",
        description="Virtual motor 1",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-10000, 10000),
    ),
    virtual_motor_2=device(
        "nicos.devices.generic.VirtualMotor",
        description="Virtual motor 2",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-10000, 10000),
    ),
    virtual_motor_3=device(
        "nicos.devices.generic.VirtualMotor",
        description="Virtual motor 3",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-10000, 10000),
    ),
)
