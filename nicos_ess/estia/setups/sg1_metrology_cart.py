description = "Motors for the metrology cart"

pv_root = "ESTIA-SG1Ct:MC-"

devices = dict(
    approach=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Metrology Cart Rotation",
        motorpv=f"{pv_root}LinX-01:Mtr",
        has_powerauto=False,
        fmtstr="%.1f",
    ),
    position=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Metrology Cart Position",
        motorpv=f"{pv_root}RotZ-01:Mtr",
        has_powerauto=False,
    ),
    # copying this from the old setup for now until more details are given from ESTIA
    metrology_cart=device(
        "nicos.devices.generic.sequence.LockedDevice",
        description="Metrology Cart Device",
        device="position",
        lock="approach",
        unlockvalue=60.0,
        lockvalue=180.0,
    ),
)
