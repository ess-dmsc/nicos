description = "The sample alignment stack for DREAM"
prefix = "IOC"

devices = dict(
    pos_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="X axis alignment",
        motorpv=f"{prefix}:m1",
    ),
    pos_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Y axis alignment",
        motorpv=f"{prefix}:m2",
    ),
    pos_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Z axis alignment",
        motorpv=f"{prefix}:m3",
    ),
)
