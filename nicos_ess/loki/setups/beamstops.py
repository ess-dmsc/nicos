description = "Beamstop system for LoKI"

pv_root = "TBD"
detector_beamstop_pv_root = f"{pv_root}-DtBS1:"

devices = dict(
    beamstop_selector=device(
        "nicos.devices.generic.switcher.MultiSwitcher",
        moveables=[
            "detector_beamstop_z1",
            "detector_beamstop_z2",
            "detector_beamstop_z3",
            "detector_beamstop_z4",
            "detector_beamstop_z5",
        ],
    ),
    detector_beamstop_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop X - electrical axis 3 in motion cabinet 5",
        motorpv=f"{detector_beamstop_pv_root}MC-LinX-01:Mtr",
        monitor_deadband=0.01,
    ),
    detector_beamstop_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Y - electrical axis 4 in motion cabinet 5",
        motorpv=f"{detector_beamstop_pv_root}MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    detector_beamstop_z1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z1 M4 Transmission - electrical axis 5 in motion cabinet 5",
        motorpv=f"{detector_beamstop_pv_root}MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    detector_beamstop_z2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z2 20x25 - electrical axis 6 in motion cabinet 5",
        motorpv=f"{detector_beamstop_pv_root}MC-LinZ-02:Mtr",
        monitor_deadband=0.01,
    ),
    detector_beamstop_z3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z3 50x60 - electrical axis 7 in motion cabinet 5",
        motorpv=f"{detector_beamstop_pv_root}MC-LinZ-03:Mtr",
        monitor_deadband=0.01,
    ),
    detector_beamstop_z4=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z4 65x75 - electrical axis 8 in motion cabinet 5",
        motorpv=f"{detector_beamstop_pv_root}MC-LinZ-04:Mtr",
        monitor_deadband=0.01,
    ),
    detector_beamstop_z5=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z5 100x105 - electrical axis 9 in motion cabinet 5",
        motorpv=f"{detector_beamstop_pv_root}MC-LinZ-05:Mtr",
        monitor_deadband=0.01,
    ),
)
