description = "The motors for alignment in the DEMO cave"

devices = dict(
    mX=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Single axis positioner",
        motorpv="DEMO-SpScn:MC-X-01:Mtr",
    ),
    mY=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Single axis positioner",
        motorpv="DEMO-SpScn:MC-Y-01:Mtr",
    ),
    mZ=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Single axis positioner",
        motorpv="DEMO-SpScn:MC-Z-01:Mtr",
    ),
)
