description = "Motors for the metrology cart of selene guide 2"

pv_approach = "ESTIA-SG2Ct:MC-RotZ-01:Mtr"
pv_position = "ESTIA-SG2Ct:MC-LinX-01:Mtr"

devices = dict(
    meas_cart_approach2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rotator for approach",
        motorpv=pv_approach,
    ),
    meas_cart_approach_controller_2=device(
        "nicos_ess.devices.mapped_controller.MappedControllerEngageDisengage",
        description="Engage/disengage approach",
        controlled_device="meas_cart_approach2",
        mapping={
            "Disengage": 0.0,
            "Engage": 210.0,
        },
    ),
    meas_cart_position2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Cart positioning",
        motorpv=pv_position,
    ),
    mcart2=device(
        "nicos.devices.generic.sequence.LockedDevice",
        description="Metrology Cart device",
        device="meas_cart_position2",
        lock="meas_cart_approach2",
        unlockvalue=60.0,
        lockvalue=180.0,
    ),
    measurement_clutch2=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Metrology Cart 2 clutch",
        readpv=f"{pv_position}-OpenClutch",
        writepv=f"{pv_position}-OpenClutch",
    ),
)
