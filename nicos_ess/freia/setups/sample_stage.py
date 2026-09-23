description = "Sample Stage Motions"

devices = dict(
    sample_position_lift=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample Positioner Y atop the hexapod",
        motorpv="FREIA-SpLin:MC-LinY-01:Mtr",
    ),
)
