description = "Inverted Guide Alignment Motors"
prefix = "FREIA-InvGde:MC-"

devices = dict(
    inv_guide_translation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Inverted Guide Translation",
        motorpv=f"{prefix}LinZ-01:Mtr",
    ),
    inv_guide_rotation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Inverted Guide Rotation",
        motorpv=f"{prefix}RotY-01:Mtr",
    ),
)
