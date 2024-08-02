description = "top sample table devices"

includes = ["sample_table_1"]

group = "optional"

devices = dict(
    st2_z=device(
        "nicos.devices.generic.Axis",
        description="table 2 z axis",
        pollinterval=15,
        maxage=60,
        fmtstr="%.2f",
        abslimits=(-10, 10),
        precision=0.01,
        motor="st2_zmot",
    ),
    st2_zmot=device(
        "nicos.devices.generic.VirtualMotor",
        description="sample table 2 z motor",
        fmtstr="%.2f",
        abslimits=(-10, 10),
        visibility=(),
        unit="mm",
    ),
    st2_y=device(
        "nicos.devices.generic.Axis",
        description="table 2 y axis",
        pollinterval=15,
        maxage=60,
        fmtstr="%.2f",
        abslimits=(-25, 25),
        precision=0.01,
        motor="st2_ymot",
    ),
    st2_ymot=device(
        "nicos.devices.generic.VirtualMotor",
        description="sample table 2 y motor",
        fmtstr="%.2f",
        abslimits=(-25, 25),
        visibility=(),
        unit="mm",
    ),
    st2_x=device(
        "nicos.devices.generic.Axis",
        description="table 2 x axis",
        pollinterval=15,
        maxage=60,
        fmtstr="%.2f",
        abslimits=(-25, 25),
        precision=0.01,
        motor="st2_xmot",
    ),
    st2_xmot=device(
        "nicos.devices.generic.VirtualMotor",
        description="sample table 2 x motor",
        fmtstr="%.2f",
        abslimits=(-25, 25),
        visibility=(),
        unit="mm",
    ),
)
