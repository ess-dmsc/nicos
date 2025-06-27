description = "Beamstop system for LoKI"

pv_root = "LOKI-DtBS1:"

devices = dict(
    beamstop_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop X - electrical axis 3 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinX-01:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Y - electrical axis 4 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    beam_monitor_z1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z1 M4 Transmission - electrical axis 5 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop_z2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z2 20x25 - electrical axis 6 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-02:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop_z3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z3 50x60 - electrical axis 7 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-03:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop_z4=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z4 65x75 - electrical axis 8 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-04:Mtr",
        monitor_deadband=0.01,
    ),
    beamstop_z5=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector beamstop Z5 100x105 - electrical axis 9 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinZ-05:Mtr",
        monitor_deadband=0.01,
    ),
)
