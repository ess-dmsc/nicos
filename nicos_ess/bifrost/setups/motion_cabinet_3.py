description = "Motion cabinet 3"


devices = dict(
    get_lost_tube=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Get-Lost-Tube In-Beam Positioner",
        readpv="BIFROST-InBm:MC-Pne-01:ShtAuxBits07",
        writepv="BIFROST-InBm:MC-Pne-01:ShtOpen",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    get_lost_tube_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the the Get-Lost-Tube In-Beam Positioner",
        readpv="BIFROST-InBm:MC-Pne-01:ShtMsgTxt",
    ),
    sample_stack_rotation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rotational sample stack",
        motorpv="BIFROST-SpRot:MC-RotZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    detector_tank_rotation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rotational detector tank",
        motorpv="BIFROST-DtCar:MC-RotZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_1_left=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 1 left",
        motorpv="BIFROST-DivSl1:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_1_right=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 1 right",
        motorpv="BIFROST-DivSl1:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_1=device(
        "nicos.devices.generic.slit.HorizontalGap",
        description="Divergence slit 1 abstraction device",
        opmode="2blades",
        coordinates="equal",
        left="divergence_slit_1_left",
        right="divergence_slit_1_right",
    ),
    divergence_slit_2_left=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 2 left",
        motorpv="BIFROST-DivSl2:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_2_right=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 2 right",
        motorpv="BIFROST-DivSl2:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_2=device(
        "nicos.devices.generic.slit.HorizontalGap",
        description="Divergence slit 2 abstraction device",
        opmode="2blades",
        coordinates="equal",
        left="divergence_slit_2_left",
        right="divergence_slit_2_right",
    ),
    divergence_slit_3_left=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 3 left",
        motorpv="BIFROST-DivSl3:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_3_right=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 3 right",
        motorpv="BIFROST-DivSl3:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_3=device(
        "nicos.devices.generic.slit.HorizontalGap",
        description="Divergence slit 3 abstraction device",
        opmode="2blades",
        coordinates="equal",
        left="divergence_slit_3_left",
        right="divergence_slit_3_right",
    ),
    goniometer_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Goniometer X",
        motorpv="BIFROST-SpGon:MC-RotX-01:Mtr",
        monitor_deadband=0.01,
    ),
    goniometer_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Goniometer Y",
        motorpv="BIFROST-SpGon:MC-RotY-01:Mtr",
        monitor_deadband=0.01,
    ),
)
