description = "Virtual hexapod testing"

group = "optional"

devices = dict(
    tx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tx Translation",
        abslimits=(-70, 125),
        # fmtstr="%.f",
        unit="mm",
        speed=1,
    ),
    ty=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ty Translation",
        abslimits=(-40, 40),
        # fmtstr="%.f",
        unit="mm",
        speed=1,
    ),
    tz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tz Translation",
        abslimits=(-55, 65),
        # fmtstr="%.f",
        unit="mm",
        speed=1,
    ),
    rx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rx Rotation",
        abslimits=(0, 5),
        # fmtstr="%.f",
        unit="deg",
        speed=1.5,
    ),
    ry=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ry Rotation",
        abslimits=(-12, 2.5),
        # fmtstr="%.f",
        unit="deg",
        speed=1.5,
    ),
    rz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rz Rotation",
        abslimits=(0, 0.5),
        # fmtstr="%.f",
        unit="deg",
        speed=1.5,
    ),
    hexapod=device(
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
