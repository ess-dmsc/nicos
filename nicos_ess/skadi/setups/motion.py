description = "A list of SKADI motion devices"

pv_root = "SKADI"

devices = dict(
    polarization_guide_change=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Polariser guide changer",
        motorpv=f"{pv_root}-PolChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    laser_attenuator_sledge=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Laser attenuator sledge",
        motorpv=f"{pv_root}-AttCh1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    # TODO: Not connecting
    attenuator_frame_translation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Attenuator frame translation",
        motorpv=f"{pv_root}-AttAdj:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
)
