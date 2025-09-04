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
        controlled_device="beamstop_x",
        mapping={
            "Park": 1,
            "x position bs1": 1,  # TBD
            "x position bs2": 2,  # TBD
            "x position bs3": 3,  # TBD
            "x position bs4": 4,  # TBD
            "x position bs5": 5,  # TBD
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
        controlled_device="beamstop_y",
        mapping={"In beam": 32.5},
    ),
    beamstop1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z1 M4 Transmission - electrical axis 5 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop1_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop1",
        mapping={"Park": 987.5, "In beam": 54.630},
    ),
    beamstop2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z2 20x25 - electrical axis 6 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-02:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop2_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop2",
        mapping={"Park": 977.998, "In beam": 59.320},
    ),
    beamstop3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z3 50x60 - electrical axis 7 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-03:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop3_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop3",
        mapping={"Park": 987.5, "In beam": 55.6},
    ),
    beamstop4=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z4 65x75 - electrical axis 8 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-04:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop4_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop4",
        mapping={"Park": 987, "In beam": 57.3},
    ),
    beamstop5=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z5 100x105 - electrical axis 9 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-05:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop5_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop5",
        mapping={"Park": 989.891, "In beam": 54.6},
    ),
    beamstop_selector=device(
        "nicos_ess.loki.devices.loki_beamstop_controller.LokiBeamstopController",
        controlled_devices=[
            "beamstop5_positioner",
            "beamstop4_positioner",
            "beamstop3_positioner",
            "beamstop2_positioner",
            "beamstop1_positioner",
            "beamstop_x_positioner",
            "beamstop_y_positioner",
        ],
        mapping={
            "Park all beamstops": (
                "Park",
                "Park",
                "Park",
                "Park",
                "Park",
                "Park",
                "In beam",
            ),
            "Beamstop 5": (
                "In beam",
                "Park",
                "Park",
                "Park",
                "Park",
                "x position bs5",
                "In beam",
            ),
            "Beamstop 5 + monitor": (
                "In beam",
                "Park",
                "Park",
                "Park",
                "In beam",
                "x position bs5",
                "In beam",
            ),
            "Beamstop 4": (
                "Park",
                "In beam",
                "Park",
                "Park",
                "Park",
                "x position bs4",
                "In beam",
            ),
            "Beamstop 4 + monitor": (
                "Park",
                "In beam",
                "Park",
                "Park",
                "In beam",
                "x position bs4",
                "In beam",
            ),
            "Beamstop 3": (
                "Park",
                "Park",
                "In beam",
                "Park",
                "Park",
                "x position bs3",
                "In beam",
            ),
            "Beamstop 3 + monitor": (
                "Park",
                "Park",
                "In beam",
                "Park",
                "In beam",
                "x position bs3",
                "In beam",
            ),
            "Beamstop 2": (
                "Park",
                "Park",
                "Park",
                "In beam",
                "Park",
                "x position bs2",
                "In beam",
            ),
            "Beamstop 2 + monitor": (
                "Park",
                "Park",
                "Park",
                "In beam",
                "In beam",
                "x position bs2",
                "In beam",
            ),
            "Beamstop 1": (
                "Park",
                "Park",
                "Park",
                "Park",
                "In beam",
                "x position bs1",
                "In beam",
            ),
        },
        default_target="Park all beamstops",
    ),
)
