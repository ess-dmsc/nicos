description = "LoKI sample changer"

devices = dict(
    linear_stage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Linear sample changer - electrical axis 9 in motion cabinet 3",
        motorpv="LOKI-SpChg1:MC-LinY-01",
        monitor_deadband=0.01,
    ),
    rotation_stage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rotation sample changer - electrical axis 8 in motion cabinet 3",
        motorpv="LOKI-SpRot1:MC-RotZ-01",
        monitor_deadband=0.01,
    ),
    cell_rotation_stage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rotation sample cell - electrical axis 11 in motion cabinet 3",
        motorpv="LOKI-SpCel1:MC-RotX-01",
        monitor_deadband=0.01,
    ),
)
