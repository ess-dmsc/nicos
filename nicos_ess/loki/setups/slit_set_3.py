description = "Slit set 3"

group = "optional"

devices = dict(
    slits_3_u=device(
        "nicos.devices.generic.VirtualMotor",
        description="Upper edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-10, 43),
        visibility=(),
    ),
    slits_3_b=device(
        "nicos.devices.generic.VirtualMotor",
        description="Bottom edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-43, 10),
        visibility=(),
    ),
    slits_3_l=device(
        "nicos.devices.generic.VirtualMotor",
        description="Left edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-26, 10),
        visibility=(),
    ),
    slits_3_r=device(
        "nicos.devices.generic.VirtualMotor",
        description="Right edge of slit set",
        fmtstr="%.2f",
        unit="mm",
        speed=0.5,
        abslimits=(-10, 26),
        visibility=(),
    ),
    slits_3=device(
        "nicos.devices.generic.Slit",
        description="Slit set with 4 blades",
        left="slits_3_l",
        right="slits_3_r",
        bottom="slits_3_b",
        top="slits_3_u",
        opmode="centered",
    ),
)
