description = "Virtual hexapod with added Translation"

group = "optional"

devices = dict(
    tx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tx Translation",
        abslimits=(-70, 125),
        unit="mm",
    ),
    ty=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ty Translation",
        abslimits=(-40, 40),
        unit="mm",
    ),
    tz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tz Translation",
        abslimits=(-55, 65),
        unit="mm",
    ),
    rx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rx Rotation",
        abslimits=(0, 5),
        unit="deg",
    ),
    ry=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ry Rotation",
        abslimits=(-12, 2.5),
        unit="deg",
    ),
    rz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rz Rotation",
        abslimits=(0, 0.5),
        unit="deg",
    ),
    six_dof_hexapod=device(
        "nicos_ess.devices.virtual.hexapod.VirtualHexapod",
        description="Hexapod Device",
        tx="tx",
        ty="ty",
        tz="tz",
        rx="rx",
        ry="ry",
        rz="rz",
    ),
)
