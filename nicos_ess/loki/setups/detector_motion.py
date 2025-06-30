description = "Detector carriage motor"

pv_root = "LOKI-DtCar1:"

devices = dict(
    detector_carriage=device(
        "nicos_ess.loki.devices.detector_motion.LOKIDetectorMotion",
        description="Detector carriage - electrical axis 1 in motion cabinet 5",
        motorpv=f"{pv_root}MC-LinX-01:Mtr",
        monitor_deadband=0.01,
        ps_bank_name="PS_Bank_0",
    )
)
