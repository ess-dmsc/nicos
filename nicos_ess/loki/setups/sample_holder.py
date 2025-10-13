description = "LoKI sample holder"

group = "optional"

includes = ["sample_stack"]

devices = dict(
    linear_sample_changer=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Linear sample changer - electrical axis 9 in motion cabinet 3",
        motorpv="LOKI-SpChg1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_rotation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsJogMotor",
        description="Rotation sample cell - electrical axis 11 in motion cabinet 3",
        motorpv="LOKI-SpCel1:MC-RotX-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_rotation_rpm=device(
        "nicos_ess.devices.transformer_devices.DegreesPerSecondToRPM",
        motor="sample_rotation",
    ),
    thermostated_sample_holder=device(
        "nicos_ess.loki.devices.thermostated_cellholder.ThermoStatedCellHolder",
        description="The thermostated sample-holder for LoKI",
        xmotor="linear_sample_changer",
        ymotor="sample_stack_z",
        precision=[0.05, 0.05],
    ),
)
