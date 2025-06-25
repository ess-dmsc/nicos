description = "Detector carriage motor"

pv_root = "LOKI-DtCar1:"

devices = dict(
    detector_carriage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector carriage - electrical axis 1 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinX-01:Mtr",
        monitor_deadband=0.01,
    )
)
