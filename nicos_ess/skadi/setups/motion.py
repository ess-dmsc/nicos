description = "A list of SKADI motion devices"

pv_root = "SKADI-"

devices = dict(
    polarizer_guide=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Polarisation Guide Changer",
        motorpv=f"{pv_root}PolChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    attenuator=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Laser+Attenuator sledge",
        motorpv=f"{pv_root}AttCh1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    # TODO: Not connecting
    attenuation_setting=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Attenuator frame translation",
        motorpv=f"{pv_root}AttAdj:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    # TODO: Check user name and desc in ToM
    collimation_changer_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 1",
        motorpv=f"{pv_root}ColCh1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 2",
        motorpv=f"{pv_root}ColCh2:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 3",
        motorpv=f"{pv_root}ColCh3:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_4=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 4",
        motorpv=f"{pv_root}ColCh4:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_5=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 5",
        motorpv=f"{pv_root}ColCh5:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_6_VSANS=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 6 (VSANS)",
        motorpv=f"{pv_root}ColCh6:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimation_changer_7_VSANS_angle=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Changer 7 (VSANS angle)",
        motorpv=f"{pv_root}ColCh7:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    # TODO: Check user name and desc in ToM
    translation_X_detector_LA=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector Carriage 1",
        motorpv=f"{pv_root}DtCar1:MC-LinX-01:Mtr",
        monitor_deadband=0.01,
    ),
    translation_X_detector_MA=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector Carriage 2",
        motorpv=f"{pv_root}DtCar2:MC-LinX-01:Mtr",
        monitor_deadband=0.01,
    ),
    translation_Y_detector_LA=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector Carriage 1",
        motorpv=f"{pv_root}DtCar1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    translation_Z_detector_LA=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector Carriage 1",
        motorpv=f"{pv_root}DtCar1:MC-LftZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    translation_Y_detector_MA=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector Carriage 2",
        motorpv=f"{pv_root}DtCar2:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    translation_Z_detector_MA=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector Carriage 2",
        motorpv=f"{pv_root}DtCar2:MC-LftZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    translation_Y_beamstop=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Beam Stop Positioning",
        motorpv=f"{pv_root}DtBS1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    translation_Z_beamstop=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Beam Stop Positioning",
        motorpv=f"{pv_root}DtBS1:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    M3_in_beam_positioner=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="M3 In-beam positioner",
        writepv=f"{pv_root}InBmM3:MC-Pne-01:ShtOpen",
        readpv=f"{pv_root}InBmM3:MC-Pne-01:ShtAuxBits07",
        statuspv=f"{pv_root}InBmM3:MC-Pne-01:ShtStatusCode",
        resetpv=f"{pv_root}InBmM3:MC-Pne-01:ShtErrRst",
        msgtxt=f"{pv_root}InBmM3:MC-Pne-01:ShtMsgTxt",
    ),
    detector_tank_window_cover=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Detector Tank Window Cover",
        writepv=f"{pv_root}InBmWC:MC-Pne-01:ShtOpen",
        readpv=f"{pv_root}InBmWC:MC-Pne-01:ShtAuxBits07",
        statuspv=f"{pv_root}InBmWC:MC-Pne-01:ShtStatusCode",
        resetpv=f"{pv_root}InBmWC:MC-Pne-01:ShtErrRst",
        msgtxt=f"{pv_root}InBmWC:MC-Pne-01:ShtMsgTxt",
    ),
    # TODO: Not connecting
    sample_stack_height=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample stack linear z main",
        motorpv=f"{pv_root}SpSt1I:MC-LftZ-02:Mtr",
        monitor_deadband=0.01,
    ),
    # TODO: Anciliary?
    # TODO: Hexapode?
    # TODO: Snout?
)
