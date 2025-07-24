description = "Virtual hexapod testing"

group = "optional"

devices = dict(
    tx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tx Translation",
        abslimits=(-70, 125),
        # fmtstr="%.f",
        unit="mm",
    ),
    ty=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ty Translation",
        abslimits=(-40, 40),
        # fmtstr="%.f",
        unit="mm",
    ),
    tz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tz Translation",
        abslimits=(-55, 65),
        # fmtstr="%.f",
        unit="mm",
    ),
    rx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rx Rotation",
        abslimits=(0, 5),
        # fmtstr="%.f",
        unit="deg",
    ),
    ry=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ry Rotation",
        abslimits=(-12, 2.5),
        # fmtstr="%.f",
        unit="deg",
    ),
    rz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rz Rotation",
        abslimits=(0, 0.5),
        # fmtstr="%.f",
        unit="deg",
    ),
    table=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Table Translation",
        abslimits=(0, 300),
        # fmtstr="%.f",
        unit="mm",
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
