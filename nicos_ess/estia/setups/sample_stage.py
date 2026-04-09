description = "Sample stage system made up of Newport Hexapod and Goinometer Sample Rotation Stage"

pv_root = "ESTIA-SES:MC-MCU-001:"

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
        motorpv=f"{pv_root}m1",
        has_powerauto=False,
        fmtstr="%.2f",
    ),
    ty=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Ty Translation",
        motorpv=f"{pv_root}m2",
        has_powerauto=False,
        fmtstr="%.2f",
    ),
    tz=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Tz Translation",
        motorpv=f"{pv_root}m3",
        has_powerauto=False,
        fmtstr="%.2f",
    ),
    rx=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rx Rotation",
        motorpv=f"{pv_root}m4",
        has_powerauto=False,
        fmtstr="%.2f",
    ),
    ry=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Ry Rotation",
        motorpv=f"{pv_root}m5",
        has_powerauto=False,
        fmtstr="%.2f",
    ),
    rz=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rz Rotation",
        motorpv=f"{pv_root}m6",
        has_powerauto=False,
        fmtstr="%.2f",
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
)
