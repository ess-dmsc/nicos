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
            "Parked": 1,
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
        mapping={"Parked": 987.5, "In beam": 54.630},
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
        mapping={"Parked": 977.998, "In beam": 59.320},
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
        mapping={"Parked": 987.5, "In beam": 55.6},
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
        mapping={"Parked": 987, "In beam": 57.3},
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
        mapping={"Parked": 989.891, "In beam": 54.6},
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
                "Parked",
                "Parked",
                "Parked",
                "Parked",
                "Parked",
                "Parked",
                "In beam",
            ),
            "Beamstop 5": (
                "In beam",
                "Parked",
                "Parked",
                "Parked",
                "Parked",
                "x position bs5",
                "In beam",
            ),
            "Beamstop 5 + monitor": (
                "In beam",
                "Parked",
                "Parked",
                "Parked",
                "In beam",
                "x position bs5",
                "In beam",
            ),
            "Beamstop 4": (
                "Parked",
                "In beam",
                "Parked",
                "Parked",
                "Parked",
                "x position bs4",
                "In beam",
            ),
            "Beamstop 4 + monitor": (
                "Parked",
                "In beam",
                "Parked",
                "Parked",
                "In beam",
                "x position bs4",
                "In beam",
            ),
            "Beamstop 3": (
                "Parked",
                "Parked",
                "In beam",
                "Parked",
                "Parked",
                "x position bs3",
                "In beam",
            ),
            "Beamstop 3 + monitor": (
                "Parked",
                "Parked",
                "In beam",
                "Parked",
                "In beam",
                "x position bs3",
                "In beam",
            ),
            "Beamstop 2": (
                "Parked",
                "Parked",
                "Parked",
                "In beam",
                "Parked",
                "x position bs2",
                "In beam",
            ),
            "Beamstop 2 + monitor": (
                "Parked",
                "Parked",
                "Parked",
                "In beam",
                "In beam",
                "x position bs2",
                "In beam",
            ),
            "Beamstop 1": (
                "Parked",
                "Parked",
                "Parked",
                "Parked",
                "In beam",
                "x position bs1",
                "In beam",
            ),
        },
        all_parked_mapping="Park all beamstops",
    ),
)
