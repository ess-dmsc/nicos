description = "Virtual hexapod with added Translation"

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
    mock_estia_hexapod=device(
        "nicos_ess.devices.virtual.hexapod.TableHexapod",
        description="Hexapod Device",
        tx="mock_tx",
        ty="mock_ty",
        tz="mock_tz",
        rx="mock_rx",
        ry="mock_ry",
        rz="mock_rz",
        table="mock_goniometer",
    ),
    hexapod_status=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="NewPort Status",
        readpv=f"ESTIA-SES:MC-MCU-001:STATUS",
    ),
)
