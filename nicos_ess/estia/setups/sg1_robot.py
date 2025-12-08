description = "Motors for the selene guide 1 robot screw adjuster"

pv_root = "ESTIA-SG1Rb:MC-"

devices = dict(
    robot_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Selene 1 Robot Position X",
        motorpv=f"{pv_root}LinX-01:Mtr",
    ),
    robot_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Selene 1 Robot Position Y",
        motorpv=f"{pv_root}LinY-01:Mtr",
    ),
    robot_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Selene 1 Robot Position Z",
        motorpv=f"{pv_root}LinZ-01:Mtr",
    ),
    r1_approach_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Selene 1 Robot Screw 2 Approach Y",
        motorpv=f"{pv_root}LinY-01:Mtr",
    ),
    r1_adjust_ry=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Selene 1 Robot Screw 1 Adjust RY",
        motorpv=f"{pv_root}RotY-01:Mtr",
    ),
    r2_approach_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Selene 1 Robot Screw 2 Approach Y ",
        motorpv=f"{pv_root}LinY-02:Mtr",
    ),
    r2_adjust_ry=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Selene 1 Robot Screw 2 Adjust RY",
        motorpv=f"{pv_root}RotY-02:Mtr",
    ),
)
