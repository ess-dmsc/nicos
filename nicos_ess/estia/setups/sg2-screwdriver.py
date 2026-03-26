description = "Motors for Screwdriver2"

pvprefix = "ESTIA-SG2Rb:MC-"

devices = dict(
    robot2_pos=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Robot horizontal positioning",
        motorpv=f"{pvprefix}LinX-01:Mtr",
    ),
    robot2_vert=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Robot vertical positioning",
        motorpv=f"{pvprefix}LinZ-01:Mtr",
    ),
    driver2_1_adjust=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Driver1-1 Adjust",
        motorpv=f"{pvprefix}RotY-01:Mtr",
    ),
    driver2_1_approach=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Driver1-1 Approach",
        motorpv=f"{pvprefix}LinY-01:Mtr",
    ),
    driver2_1_hex_state=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Hexscrew state",
        readpv=f"{pvprefix}LinY-01:Mtr-MsgTxt",
    ),
    driver2_2_adjust=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Driver1-2 Adjust",
        motorpv=f"{pvprefix}RotY-02:Mtr",
    ),
    driver2_2_approach=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Driver1-2 Approach",
        motorpv=f"{pvprefix}LinY-02:Mtr",
    ),
    driver2_2_hex_state=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Hexscrew state",
        readpv=f"{pvprefix}LinY-02:Mtr-MsgTxt",
    ),
    rclutch2=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Robot 2 clutch",
        readpv=f"{pvprefix}LinX-01:Mtr-OpenClutch",
        writepv=f"{pvprefix}LinX-01:Mtr-OpenClutch",
    ),
)
