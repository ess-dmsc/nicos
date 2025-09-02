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
    beamstop_y=device(  # offset = -32.5
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Beamstop motor horizontal axis - electrical axis 4 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop_y_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop_y",
        mapping={"In beam": 0},
    ),
    beamstop1=device(  # offset = -54.630
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z1 M4 Transmission - electrical axis 5 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop1_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop1",
        mapping={"Park": 932.87, "In beam": 0},  # park position = 987.5 + offset
    ),
    beamstop2=device(  # offset = -59.320
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z2 20x25 - electrical axis 6 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-02:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop2_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop2",
        mapping={"Park": 918.678, "In beam": 0},  # park pos = 977.998 + offset
    ),
    beamstop3=device(  # offset = -55.600
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z3 50x60 - electrical axis 7 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-03:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop3_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop3",
        mapping={"Park": 931.9, "In beam": 0},  # park position = 987.5 + offset
    ),
    beamstop4=device(  # offset = -57.300
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z4 65x75 - electrical axis 8 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-04:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop4_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop4",
        mapping={"Park": 929.7, "In beam": 0},  # park position = 987 + offset
    ),
    beamstop5=device(  # offset = -54.600
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z5 100x105 - electrical axis 9 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-05:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop5_positioner=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop5",
        mapping={"Park": 935.29, "In beam": 0},  # park position = 989.891 + offset
    ),
    beamstop_selector=device(
        "nicos_ess.devices.mapped_controller.MultiTargetMapping",
        controlled_devices=[
            "beamstop_x_positioner",
            "beamstop_y_positioner",
            "beamstop1_positioner",
            "beamstop2_positioner",
            "beamstop3_positioner",
            "beamstop4_positioner",
            "beamstop5_positioner",
        ],
        mapping={
            "Park all beamstops": (
                "Park",
                "In beam",
                "Park",
                "Park",
                "Park",
                "Park",
                "Park",
            ),
            "Beamstop 1": (
                "x position bs1",
                "In beam",
                "In beam",
                "Park",
                "Park",
                "Park",
                "Park",
            ),
            "Beamstop 2": (
                "x position bs2",
                "In beam",
                "Park",
                "In beam",
                "Park",
                "Park",
                "Park",
            ),
            "Beamstop 3": (
                "x position bs3",
                "In beam",
                "Park",
                "Park",
                "In beam",
                "Park",
                "Park",
            ),
            "Beamstop 4": (
                "x position bs4",
                "In beam",
                "Park",
                "Park",
                "Park",
                "In beam",
                "Park",
            ),
            "Beamstop 5": (
                "x position bs5",
                "In beam",
                "Park",
                "Park",
                "Park",
                "Park",
                "In beam",
            ),
        },
        default_target="Park all beamstops",
    ),
)
