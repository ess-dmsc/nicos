description = "Beamstop system for LoKI"

pv_root = "LOKI-DtBS1:"

devices = dict(
    beamstop_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop X - electrical axis 3 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinX-01:Mtr",
        monitor_deadband=0.01,
        speed=5,
    ),
    beamstop_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Y - electrical axis 4 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinY-01:Mtr",
        monitor_deadband=0.01,
        speed=4,
    ),
    beam_monitor_z1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z1 M4 Transmission - electrical axis 5 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
        speed=15,
    ),
    beam_monitor_z1_controller=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beam_monitor_z1",
        mapping={"parked": 20, "in-beam": 1000},
    ),
    beamstop_z2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z2 20x25 - electrical axis 6 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-02:Mtr",
        monitor_deadband=0.01,
        speed=10,
    ),
    beamstop_z2_controller=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop_z2",
        mapping={"parked": 20, "in-beam": 1000},
    ),
    beamstop_z3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z3 50x60 - electrical axis 7 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-03:Mtr",
        monitor_deadband=0.01,
        speed=10,
    ),
    beamstop_z3_controller=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop_z3",
        mapping={"parked": 20, "in-beam": 1000},
    ),
    beamstop_z4=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z4 65x75 - electrical axis 8 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-04:Mtr",
        monitor_deadband=0.01,
        speed=10,
    ),
    beamstop_z4_controller=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop_z4",
        mapping={"parked": 20, "in-beam": 1000},
    ),
    beamstop_z5=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z5 100x105 - electrical axis 9 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-05:Mtr",
        monitor_deadband=0.01,
        speed=10,
    ),
    beamstop_z5_controller=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="beamstop_z5",
        mapping={"parked": 20, "in-beam": 1000},
    ),
    beamstop_selector=device(
        "nicos_ess.devices.mapped_controller.MultiTargetMapping",
        controlled_devices=[
            "beamstop_z2_controller",
            "beamstop_z3_controller",
            "beamstop_z4_controller",
            "beamstop_z5_controller",
        ],
        mapping={
            "no_beamstop": ("parked", "parked", "parked", "parked"),
            "beamstop_z2": ("in-beam", "parked", "parked", "parked"),
            "beamstop_z3": ("parked", "in-beam", "parked", "parked"),
            "beamstop_z4": ("parked", "parked", "in-beam", "parked"),
            "beamstop_z5": ("parked", "parked", "parked", "in-beam"),
        },
    ),
)
