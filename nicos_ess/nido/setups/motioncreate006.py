# ruff: noqa: F821
description = "Single motor for motor timestamp test"


devices = dict(
    motor006=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample changer",
        motorpv="LabS-MCAG:MC-MCU-06:m1",
        monitor_deadband=0.01,
    ),
)
