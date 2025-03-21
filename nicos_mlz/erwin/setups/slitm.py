description = "Monochromator slit"

group = "optional"

devices = dict(
    slitm=device(
        "nicos.devices.generic.Slit",
        description="B4C slit",
        bottom=device(
            "nicos.devices.generic.Axis",
            motor=device(
                "nicos.devices.generic.VirtualMotor",
                abslimits=(0, 75),
                unit="mm",
            ),
            precision=0.01,
        ),
        top=device(
            "nicos.devices.generic.Axis",
            motor=device(
                "nicos.devices.generic.VirtualMotor",
                abslimits=(0, 75),
                unit="mm",
            ),
            precision=0.01,
        ),
        left=device(
            "nicos.devices.generic.Axis",
            motor=device(
                "nicos.devices.generic.VirtualMotor",
                abslimits=(0, 25),
                unit="mm",
            ),
            precision=0.01,
        ),
        right=device(
            "nicos.devices.generic.Axis",
            motor=device(
                "nicos.devices.generic.VirtualMotor",
                abslimits=(0, 25),
                unit="mm",
            ),
            precision=0.01,
        ),
    ),
)
