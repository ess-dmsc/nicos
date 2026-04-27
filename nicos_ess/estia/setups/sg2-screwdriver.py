description = "Motors for Screwdriver2"

pvprefix = "ESTIA-SG2Rb:MC-"

devices = dict(
    sg2_robot_pos=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Robot horizontal positioning",
        motorpv=f"{pvprefix}LinX-01:Mtr",
    ),
    sg2_robot_vert=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Robot vertical positioning",
        motorpv=f"{pvprefix}LinZ-01:Mtr",
    ),
    sg2_screwdriver_adjust_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Driver1-1 Adjust",
        motorpv=f"{pvprefix}RotY-01:Mtr",
    ),
    sg2_screwdriver_approach_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Driver1-1 Approach",
        motorpv=f"{pvprefix}LinY-01:Mtr",
    ),
    sg2_screwdriver_approach_1_controller=device(
        "nicos_ess.devices.mapped_controller.MappedControllerEngageDisengage",
        description="Engage/disengage approach",
        controlled_device="sg2_screwdriver_approach_1",
        mapping={
            "Disengage": -29.0,
            "Engage": 0.0,
        },
    ),
    sg2_screwdriver_hex_state_1=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Hexscrew state",
        readpv=f"{pvprefix}LinY-01:Mtr-MsgTxt",
    ),
    sg2_screwdriver_adjust_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Driver1-2 Adjust",
        motorpv=f"{pvprefix}RotY-02:Mtr",
    ),
    sg2_screwdriver_approach_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Driver1-2 Approach",
        motorpv=f"{pvprefix}LinY-02:Mtr",
    ),
    sg2_screwdriver_approach_2_controller=device(
        "nicos_ess.devices.mapped_controller.MappedControllerEngageDisengage",
        description="Engage/disengage approach",
        controlled_device="sg2_screwdriver_approach_2",
        mapping={
            "Disengage": -28.0,
            "Engage": 0.0,
        },
    ),
    sg2_screwdriver_hex_state_2=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Hexscrew state",
        readpv=f"{pvprefix}LinY-02:Mtr-MsgTxt",
    ),
    sg2_robot_clutch=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Robot 2 clutch",
        readpv=f"{pvprefix}LinX-01:Mtr-OpenClutch",
        writepv=f"{pvprefix}LinX-01:Mtr-OpenClutch",
    ),
)
