description = (
    "Sample Environment Axis for The Solid Liquid Sample Changer "
    "and the Room Temperature Sample Changer"
)

devices = dict(
    horizontal_adjust=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample Environment Axis",
        motorpv="ESTIA-SpSt:MC-LinY-01:Mtr",
    ),
)
