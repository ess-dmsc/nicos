description = "LoKI sample stack"

pv_root = "LOKI-SpSt1:"

devices = dict(
    sample_stack_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample stack linear x - electrical axis 3 in motion cabinet 4",
        motorpv=f"{pv_root}MC-LinX-01",
        monitor_deadband=0.01,
    ),
    sample_stack_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample stack linear y - electrical axis 4 in motion cabinet 4",
        motorpv=f"{pv_root}MC-LinY-01",
        monitor_deadband=0.01,
    ),
    sample_stack_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample stack linear z - electrical axis 1 in motion cabinet 4",
        motorpv=f"{pv_root}MC-LinZ-01",
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
            "default_loading_position": (0, 0, 0),
            "default_center_position": (1, 1, 1),
        },
    ),
)
