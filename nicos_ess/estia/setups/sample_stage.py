description = "Sample stage system made up of Newport Hexapod and Goinometer Sample Rotation Stage"

hex_root = "ESTIA-SES:MC-MCU-001:"

devices = dict(
    goinometer=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample Stage Rotation Base",
        motorpv=f"ESTIA-SpRot:MC-RotZ01:Mtr",
        has_powerauto=False,
        fmtstr="%.2f",
    ),
    tx=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Tx Translation",
        motorpv=f"{hex_root}m1",
        has_powerauto=False,
        fmtstr="%.2f",
        visibility=(),
    ),
    ty=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Ty Translation",
        motorpv=f"{hex_root}m2",
        has_powerauto=False,
        fmtstr="%.2f",
        visibility=(),
    ),
    tz=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Tz Translation",
        motorpv=f"{hex_root}m3",
        has_powerauto=False,
        fmtstr="%.2f",
        visibility=(),
    ),
    rx=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rx Rotation",
        motorpv=f"{hex_root}m4",
        has_powerauto=False,
        fmtstr="%.2f",
        visibility=(),
    ),
    ry=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Ry Rotation",
        motorpv=f"{hex_root}m5",
        has_powerauto=False,
        fmtstr="%.2f",
        visibility=(),
    ),
    rz=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rz Rotation",
        motorpv=f"{hex_root}m6",
        has_powerauto=False,
        fmtstr="%.2f",
        visibility=(),
    ),
    estia_hexapod=device(
        "nicos_ess.devices.virtual.hexapod.TableHexapod",
        description="Hexapod Device",
        tx="tx",
        ty="ty",
        tz="tz",
        rx="rx",
        ry="ry",
        rz="rz",
        table="goinometer",
    ),
    hexapod_status=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="NewPort Status",
        readpv=f"{hex_root}STATUS",
    ),
    hexapod_coordinate_state=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Current coordinate system",
        readpv=f"{hex_root}CS",
        writepv=f"{hex_root}CS",
    ),
)
