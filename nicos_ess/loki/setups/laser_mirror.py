description = "LoKI Laser mirror"

group = "optional"

devices = dict(
    alignment_laser_mirror=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Motor changing laser mirror for alignment - electrical axis 5 in motion cabinet 3",
        motorpv="InBmLM:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
)
