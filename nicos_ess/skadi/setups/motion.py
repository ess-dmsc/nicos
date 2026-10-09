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
    collimation_changer_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 1",
        motorpv=f"{pv_root}-ColCh1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 2",
        motorpv=f"{pv_root}-ColCh2:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 3",
        motorpv=f"{pv_root}-ColCh3:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_4=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 4",
        motorpv=f"{pv_root}-ColCh4:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_5=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 5",
        motorpv=f"{pv_root}-ColCh5:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_6_VSANS=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 6 (VSANS)",
        motorpv=f"{pv_root}-ColCh6:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_7_VSANS_angle=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 7 (VSANS angle)",
        motorpv=f"{pv_root}-ColCh7:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
)
