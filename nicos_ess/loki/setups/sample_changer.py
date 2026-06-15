description = "LoKI sample changer"

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
        description="Rotation sample cell - transformed to rpm",
        motor="sample_rotation",
    ),
    sample_changer=device(
        "nicos_ess.loki.devices.thermostated_cellholder.ThermoStatedCellHolder",
        description="The thermostated sample changer for LoKI",
        xmotor="linear_sample_changer",
        ymotor="sample_stack_z",
        precision=[0.05, 0.05],
        nexus_config=[
            {
                "nexus_path": "/entry/sample",
                "group_name": "sample_changer",
                "nx_class": "NXcollection",
                "suffix": "position_readback",
                "dataset_type": "static_read",
            }
        ],
    ),
)
