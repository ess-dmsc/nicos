description = "LoKI sample holder"

group = "optional"

devices = dict(
    linear_sample_changer=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Linear sample changer - electrical axis 9 in motion cabinet 3",
        motorpv="LOKI-SpChg1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_stack_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample stack linear z - electrical axis 1 in motion cabinet 4",
        motorpv=f"LOKI-SpSt1:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    thermostated_sample_holder=device(
        "nicos_ess.loki.devices.thermostated_cellholder.ThermoStatedCellHolder",
        description="The thermostated sample-holder for LoKI",
        xmotor="linear_sample_changer",
        ymotor="sample_stack_z",
        precision=[0.05, 0.05],
        nexus_config=[
            {
                "group_name": "thermostated_sample_holder",
                "nx_class": "NXcollection",
                "suffix": "readback",
                "dataset_type": "static_read",
            }
        ],
    ),
)
