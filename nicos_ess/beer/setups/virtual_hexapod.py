description = "Virtual hexapod testing"

group = "optional"

devices = dict(
    tx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tx Translation",
        abslimits=(-200, 200),
        # fmtstr="%.f",
        unit="mm",
    ),
    ty=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ty Translation",
        abslimits=(-200, 200),
        # fmtstr="%.f",
        unit="mm",
    ),
    tz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tz Translation",
        abslimits=(-23, 23),
        # fmtstr="%.f",
        unit="mm",
    ),
    rx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rx Rotation",
        abslimits=(-23, 23),
        # fmtstr="%.f",
        unit="deg",
    ),
    ry=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ry Rotation",
        abslimits=(-23, 23),
        # fmtstr="%.f",
        unit="deg",
    ),
    rz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rz Rotation",
        abslimits=(-30, 30),
        # fmtstr="%.f",
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
    ),
)
