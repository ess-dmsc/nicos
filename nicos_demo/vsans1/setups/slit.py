description = "collimation slit"

group = "lowlevel"

devices = dict(
    slit_top=device(
        "nicos.devices.generic.VirtualMotor",
        description="collimation slit top axis",
        visibility=(),
        abslimits=(0, 25),
        unit="mm",
    ),
    slit_bottom=device(
        "nicos.devices.generic.VirtualMotor",
        description="collimation slit bottom axis",
        visibility=(),
        abslimits=(0, 25),
        unit="mm",
    ),
    slit_left=device(
        "nicos.devices.generic.VirtualMotor",
        description="collimation slit left axis",
        visibility=(),
        abslimits=(0, 25),
        unit="mm",
    ),
    slit_right=device(
        "nicos.devices.generic.VirtualMotor",
        description="collimation slit right axis",
        visibility=(),
        abslimits=(0, 25),
        unit="mm",
    ),
    slit=device(
        "nicos.devices.generic.Slit",
        description="Collimation slit",
        top="slit_top",
        bottom="slit_bottom",
        left="slit_left",
        right="slit_right",
        opmode="centered",
        coordinates="opposite",
        pollinterval=5,
        maxage=12,
    ),
)
