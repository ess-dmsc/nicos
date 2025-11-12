description = "Motors for the metrology cart"

# Commenting the original testing code out for now. TODO: Delete (When Cold Commissioning Starts?)
# pvprefix = "PSI-ESTIARND:MC-MCU-01:"

# devices = dict(
#    mapproach=device(
#        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
#        description="Rotator for approach",
#        motorpv=f"{pvprefix}m12",
#        has_powerauto=False,
#        fmtstr="%.1f",
#    ),
#    mpos=device(
#        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
#        description="Cart positioning",
#        motorpv=f"{pvprefix}m13",
#        has_powerauto=False,
#    ),
#    mcart=device(
#        "nicos.devices.generic.sequence.LockedDevice",
#        description="Metrology Cart device",
#        device="mpos",
#        lock="mapproach",
#        unlockvalue=60.0,
#        lockvalue=180.0,
#    ),
# )
pv_root = "ESTIA-SG1Ct:MC-"

devices = (
    dict(
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
        # copying this from the test setup for now until more details are given from ESTIA
        # or if decision in motion is changed
        metrology_cart=device(
            "nicos.devices.generic.sequence.LockedDevice",
            description="Metrology Cart Device",
            device="position",
            lock="approach",
            unlockvalue=60.0,
            lockvalue=180.0,
        ),
    ),
)
