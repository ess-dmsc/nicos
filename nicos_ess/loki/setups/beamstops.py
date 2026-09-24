description = "Beamstop system for LoKI"

pv_root = "LOKI-DtBS1:"

devices = dict(
    beamstop_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Beamstop motor along beam axis - electrical axis 3 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinX-01:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop_x_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        description="Mapped positions for beamstop motor along beam axis",
        controlled_device="beamstop_x",
        mapping={
            "parked": 1,
            "xpos bs1": 171.23,
            "xpos bs2": 264.22,
            "xpos bs3": 233.82,
            "xpos bs4": 202,
            "xpos bs": 171.66,
        },
    ),
    beamstop_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Beamstop motor horizontal axis - electrical axis 4 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop_y_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        description="Mapped positions for beamstop motor horizontal axis",
        controlled_device="beamstop_y",
        mapping={"in-beam": 32.5},
    ),
    beamstop1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z1 M4 Transmission - electrical axis 5 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop1_positioner=device(
        "nicos_ess.loki.devices.beamstop.LokiBeamstopArmPositioner",
        description="Mapped positions for beamstop motor Z1 M4 Transmission",
        controlled_device="beamstop1",
        mapping={"parked": 987.5, "in-beam": 54.630},
    ),
    beamstop2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z2 20x25 - electrical axis 6 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-02:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop2_positioner=device(
        "nicos_ess.loki.devices.beamstop.LokiBeamstopArmPositioner",
        description="Mapped positions for beamstop motor Z2",
        controlled_device="beamstop2",
        mapping={"parked": 977.998, "in-beam": 59.320},
    ),
    beamstop3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z3 50x60 - electrical axis 7 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-03:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop3_positioner=device(
        "nicos_ess.loki.devices.beamstop.LokiBeamstopArmPositioner",
        description="Mapped positions for beamstop motor Z3",
        controlled_device="beamstop3",
        mapping={"parked": 987.5, "in-eam": 55.6},
    ),
    beamstop4=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z4 65x75 - electrical axis 8 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-04:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop4_positioner=device(
        "nicos_ess.loki.devices.beamstop.LokiBeamstopArmPositioner",
        description="Mapped positions for beamstop motor Z4",
        controlled_device="beamstop4",
        mapping={"parked": 987, "in-beam": 57.3},
    ),
    beamstop5=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z5 100x105 - electrical axis 9 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-05:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop5_positioner=device(
        "nicos_ess.loki.devices.beamstop.LokiBeamstopArmPositioner",
        description="Mapped positions for beamstop motor Z5",
        controlled_device="beamstop5",
        mapping={"parked": 989.891, "in-beam": 54.6},
    ),
    beamstop_selector=device(
        "nicos_ess.loki.devices.beamstop.LokiBeamstopController",
        bsx_positioner="beamstop_x_positioner",
        bsy_positioner="beamstop_y_positioner",
        bs1_positioner="beamstop1_positioner",
        bs2_positioner="beamstop2_positioner",
        bs3_positioner="beamstop3_positioner",
        bs4_positioner="beamstop4_positioner",
        bs5_positioner="beamstop5_positioner",
        # This mapping is a placeholder, the values are set in the class. The keys should not be edited.
        # TODO: remove the mapping argument from this setup file and use the mapping defined in the class
        mapping={
            "Park all beamstops": (),
            "Beamstop 1": (),
            "Beamstop 2": (),
            "Beamstop 2 + monitor": (),
            "Beamstop 3": (),
            "Beamstop 3 + monitor": (),
            "Beamstop 4": (),
            "Beamstop 4 + monitor": (),
            "Beamstop 5": (),
            "Beamstop 5 + monitor": (),
        },
    ),
)
