description = "Sample manipulation stage"

group = "lowlevel"

devices = dict(
    sample_x_m=device(
        "nicos.devices.generic.VirtualMotor",
        description="Sample X translation motor",
        speed=1,
        unit="mm",
        fmtstr="%.2f",
        visibility=(),
        abslimits=(0, 300),
    ),
    sample_x=device(
        "nicos.devices.generic.Axis",
        description="Sample X translation",
        motor="sample_x_m",
        precision=0.01,
    ),
    sample_y_m=device(
        "nicos.devices.generic.VirtualMotor",
        description="Sample Y translation motor",
        speed=1,
        unit="mm",
        fmtstr="%.2f",
        visibility=(),
        abslimits=(0, 300),
    ),
    sample_y=device(
        "nicos.devices.generic.Axis",
        description="Sample Y translation",
        motor="sample_y_m",
        precision=0.01,
    ),
    rotm=device(
        "nicos.devices.generic.VirtualMotor",
        description="Sample rotation motor",
        speed=1,
        unit="deg",
        fmtstr="%.3f",
        visibility=(),
        abslimits=(-360, 360),
    ),
    rot=device(
        "nicos.devices.generic.Axis",
        description="Sample rotation",
        motor="rotm",
        precision=0.01,
    ),
)
