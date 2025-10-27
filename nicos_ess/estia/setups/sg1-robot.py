description = "Motors for the robot adjuster"

pvprefix = "PSI-ESTIARND:MC-MCU-01:"

devices = dict(
    robot_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M14 Selene1 Mover Y",
        motorpv=f"{pvprefix}m14",
        has_powerauto=False,
    ),
    robot_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M15 Selene1 Mover Z",
        motorpv=f"{pvprefix}m15",
        has_powerauto=False,
    ),
    robot_rx=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M16 Selene1 Mover Rx",
        motorpv=f"{pvprefix}m16",
        has_powerauto=False,
    ),
    robot_ry=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M17 Selene1 Mover Ry",
        motorpv=f"{pvprefix}m17",
        has_powerauto=False,
    ),
    robot_rz=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M18 Selene1 Mover Rz",
        motorpv=f"{pvprefix}m18",
        has_powerauto=False,
    ),
    clutch1=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Clutch 1",
        readpv=f"{pvprefix}m6-OpenClutch",
    ),
    clutch2=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Clutch 2",
        readpv=f"{pvprefix}m12-OpenClutch",
    ),
)
