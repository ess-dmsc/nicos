description = "Small Beam Limiter in Experimental Chamber 1"

group = "optional"

devices = dict(
    nbl_l=device(
        "nicos.devices.generic.VirtualReferenceMotor",
        description="Beam Limiter Left Blade",
        visibility=(),
        abslimits=(-250, 260),
        unit="mm",
        speed=10,
        refswitch="high",
    ),
    nbl_r=device(
        "nicos.devices.generic.VirtualReferenceMotor",
        description="Beam Limiter Right Blade",
        visibility=(),
        abslimits=(-250, 260),
        unit="mm",
        speed=10,
        refswitch="high",
    ),
    nbl_t=device(
        "nicos.devices.generic.VirtualReferenceMotor",
        description="Beam Limiter Top Blade",
        visibility=(),
        abslimits=(-250, 260),
        unit="mm",
        speed=10,
        refswitch="high",
    ),
    nbl_b=device(
        "nicos.devices.generic.VirtualReferenceMotor",
        description="Beam Limiter Bottom Blade",
        visibility=(),
        abslimits=(-250, 260),
        unit="mm",
        speed=10,
        refswitch="high",
    ),
    nbl=device(
        "nicos_mlz.nectar.devices.BeamLimiter",
        description="NECTAR Beam Limiter",
        left="nbl_l",
        right="nbl_r",
        top="nbl_t",
        bottom="nbl_b",
        opmode="centered",
        coordinates="opposite",
        pollinterval=5,
        maxage=10,
        parallel_ref=True,
    ),
)
