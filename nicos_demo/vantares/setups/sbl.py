description = "Small Beam Limiter in Experimental Chamber 1"

group = "lowlevel"

devices = dict(
    sbl_l=device(
        "nicos.devices.generic.VirtualMotor",
        description="Beam Limiter Left Blade",
        visibility=(),
        abslimits=(-250, 250),
        unit="mm",
    ),
    sbl_r=device(
        "nicos.devices.generic.VirtualMotor",
        description="Beam Limiter Right Blade",
        visibility=(),
        abslimits=(-250, 250),
        unit="mm",
    ),
    sbl_b=device(
        "nicos.devices.generic.VirtualMotor",
        description="Beam Limiter Bottom Blade",
        visibility=(),
        abslimits=(-250, 250),
        unit="mm",
    ),
    sbl_t=device(
        "nicos.devices.generic.VirtualMotor",
        description="Beam Limiter Top Blade",
        visibility=(),
        abslimits=(-250, 250),
        unit="mm",
    ),
    sbl=device(
        "nicos.devices.generic.Slit",
        description="Small Beam Limiter",
        left="sbl_l",
        right="sbl_r",
        top="sbl_t",
        bottom="sbl_b",
        opmode="offcentered",
        coordinates="opposite",
        pollinterval=5,
        maxage=10,
    ),
)
