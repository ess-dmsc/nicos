description = "Middle focus"
prefix = "ESTIA-Chg:MC-"

devices = dict(
    horizontal_adjust=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Horizontal adjust",
        motorpv=f"{prefix}LinY01:Mtr",
        visibility=(),
    ),
    vertical_adjust=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Vertical adjust",
        motorpv=f"{prefix}LinZ01:Mtr",
        visibility=(),
    ),
    in_beam_changer=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="In-Beam changer",
        motorpv=f"{prefix}RotX01:Mtr",
    ),
)
