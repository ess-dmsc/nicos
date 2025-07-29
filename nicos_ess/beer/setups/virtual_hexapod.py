description = "Virtual hexapod testing"

group = "optional"

devices = dict(
    tx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tx Translation",
        abslimits=(-200, 200),
        unit="mm",
    ),
    ty=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ty Translation",
        abslimits=(-200, 200),
        unit="mm",
    ),
    tz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tz Translation",
        abslimits=(-23, 23),
        unit="mm",
    ),
    rx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rx Rotation",
        abslimits=(-23, 23),
        unit="deg",
    ),
    ry=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ry Rotation",
        abslimits=(-23, 23),
        unit="deg",
    ),
    rz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rz Rotation",
        abslimits=(-30, 30),
        unit="deg",
    ),
    table=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rotation Stage Translation",
        abslimits=(-180, 180),
        unit="deg",
    ),
    hexapod=device(
        "nicos_ess.devices.virtual.hexapod.TableHexapod",
        description="Hexapod Device",
        tx="tx",
        ty="ty",
        tz="tz",
        rx="rx",
        ry="ry",
        rz="rz",
        table="table",
    ),
)
