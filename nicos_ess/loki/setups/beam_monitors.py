description = "LoKI beam monitors"

devices = dict(
    m2_beam_monitor=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="In-beam monitor M2 Halo - electrical axis 3 in motion cabinet 3",
        motorpv="InBmM2:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    m2_beam_monitor_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="m2_beam_monitor",
        mapping={"in-beam": 0, "out-of-beam": 1},
    ),
    # m3_in_beam_positioner=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="In-beam monitor M3 Transmission - electrical axis 4 in motion cabinet 3",
    #     motorpv="InBmM3:MC-LinZ-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
)
