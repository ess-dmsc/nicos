description = "LoKI sample stack"

group = "optional"

devices = dict(
    sample_stack_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample stack linear x - electrical axis 2 in motion cabinet 4",
        motorpv=f"LOKI-SpSt1:MC-LinX-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_stack_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample stack linear y - electrical axis 3 in motion cabinet 4",
        motorpv=f"LOKI-SpSt1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_stack_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample stack linear z - electrical axis 1 in motion cabinet 4",
        motorpv=f"LOKI-SpSt1:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_stack_positioner=device(
        "nicos_ess.devices.mapped_controller.MultiTargetMapping",
        controlled_devices=[
            "sample_stack_x",
            "sample_stack_y",
            "sample_stack_z",
        ],
        mapping={
            "default_loading_position": (2, 198, 53.75),
            "default_center_position": (2, 100, 53.75),
            # "default_sample_holder_lower": (120, 100, 198),
            # "default_sample_holder_rotation": (120, 100, 0),    # this z position is outside the motor limits
        },
    ),
)
