description = "LoKI Laser mirror"

group = "optional"

devices = dict(
    alignment_laser_mirror=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motor changing laser mirror for alignment - electrical axis 5 in motion cabinet 3",
        motorpv="LOKI-InBmLM:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    alignment_laser_mirror_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="alignment_laser_mirror",
        mapping={"in-beam": 2, "out-of-beam": 96},
    ),
)
