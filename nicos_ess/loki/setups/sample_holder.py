description = "LoKI sample holder"

group = "optional"

devices = dict(
    axis2_sample_stack_linear_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample stack linear x - electrical axis 2 in motion cabinet 4",
        motorpv=f"LOKI-SpSt1:MC-LinX-01:Mtr",
        monitor_deadband=0.01,
    ),
    axis3_sample_stack_linear_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample stack linear y - electrical axis 3 in motion cabinet 4",
        motorpv=f"LOKI-SpSt1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    axis1_sample_stack_linear_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample stack linear z - electrical axis 1 in motion cabinet 4",
        motorpv=f"LOKI-SpSt1:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_stack_positioner=device(
        "nicos_ess.devices.mapped_controller.MultiTargetMapping",
        controlled_devices=[
            "axis2_sample_stack_linear_x",
            "axis3_sample_stack_linear_y",
            "axis1_sample_stack_linear_z",
        ],
        mapping={
            "default_loading_position": (2, 198, 53.75),
            "default_center_position": (2, 100, 53.75),
            "default_sample_holder_lower": (120, 100, 198),
            "default_sample_holder_rotation": (120, 100, 0),
        },
    ),
    axis9_linear_sample_changer=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Linear sample changer - electrical axis 9 in motion cabinet 3",
        motorpv="LOKI-SpChg1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    axis11_mixer_sample_rotation_cell=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rotation sample cell - electrical axis 11 in motion cabinet 3",
        motorpv="LOKI-SpCel1:MC-RotX-01:Mtr",
        monitor_deadband=0.01,
    ),
    thermostated_sample_holder=device(
        "nicos_ess.loki.devices.thermostated_cellholder.ThermoStatedCellHolder",
        description="The thermostated sample-holder for LoKI",
        xmotor="axis9_linear_sample_changer",
        ymotor="axis1_sample_stack_linear_z",
        precision=[0.05, 0.05],
    ),
)
