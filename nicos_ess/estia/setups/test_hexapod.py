description = "Virtual hexapod"

devices = dict(
    mock_tx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tx Translation",
        abslimits=(-70, 125),
        unit="mm",
    ),
    mock_ty=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ty Translation",
        abslimits=(-40, 40),
        unit="mm",
    ),
    mock_tz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Tz Translation",
        abslimits=(-55, 65),
        unit="mm",
    ),
    mock_rx=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rx Rotation",
        abslimits=(0, 5),
        unit="deg",
    ),
    mock_ry=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Ry Rotation",
        abslimits=(-12, 2.5),
        unit="deg",
    ),
    mock_rz=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Rz Rotation",
        abslimits=(0, 0.5),
        unit="deg",
    ),
    mock_goniometer=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Table Translation",
        abslimits=(0, 360),
        unit="deg",
    ),
)
