description = "Simulated sample motors (mockup)"

group = "optional"

devices = dict(
    sim_motor_1=device(
        "nicos.devices.generic.VirtualMotor",
        description="Sim motor 1 (mockup)",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-10000, 10000),
        visibility=(),
    ),
    sim_motor_2=device(
        "nicos.devices.generic.VirtualMotor",
        description="Sim motor 2 (mockup)",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-10000, 10000),
        visibility=(),
    ),
    sim_motor_3=device(
        "nicos.devices.generic.VirtualMotor",
        description="Sim motor 3 (mockup)",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-10000, 10000),
        visibility=(),
    ),
)
