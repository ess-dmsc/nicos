description = "Large Beam Limiter in Experimental Chamber 2"

group = "lowlevel"

devices = dict(
    lbl_l=device(
        "nicos.devices.generic.VirtualMotor",
        description="Beam Limiter Left Blade",
        visibility=(),
        abslimits=(-400, 400),
        unit="mm",
    ),
    lbl_r=device(
        "nicos.devices.generic.VirtualMotor",
        description="Beam Limiter Right Blade",
        visibility=(),
        abslimits=(-400, 400),
        unit="mm",
    ),
    lbl_b=device(
        "nicos.devices.generic.VirtualMotor",
        description="Beam Limiter Bottom Blade",
        visibility=(),
        abslimits=(-400, 400),
        unit="mm",
    ),
    lbl_t=device(
        "nicos.devices.generic.VirtualMotor",
        description="Beam Limiter Top Blade",
        visibility=(),
        abslimits=(-400, 400),
        unit="mm",
    ),
    lbl=device(
        "nicos.devices.generic.Slit",
        description="Large Beam Limiter",
        left="lbl_l",
        right="lbl_r",
        top="lbl_t",
        bottom="lbl_b",
        opmode="offcentered",
        coordinates="opposite",
        pollinterval=5,
        maxage=10,
    ),
)
