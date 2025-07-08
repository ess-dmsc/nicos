
description = "Test crate #019"
 
devices = dict(
    axis_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Axis 1",
        motorpv="ECDC-TstCrt:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    axis_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Axis 2",
        motorpv="ECDC-TstCrt:MC-LinY-02:Mtr",
        monitor_deadband=0.01,
    ),
)