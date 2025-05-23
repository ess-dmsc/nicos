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
    cabinet_3_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 3 pressure 1",
        readpv="BIFROST-MCS3:MC-MCU-03:Pressure1",
    ),
    cabinet_3_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 3 pressure 2",
        readpv="BIFROST-MCS3:MC-MCU-03:Pressure2",
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
    divergence_slit_1_p=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 1 left",
        motorpv="BIFROST-DivSl1:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_1_p_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Divergence slit 1 right temperature",
        readpv="BIFROST-DivSl1:MC-SlYp-01:Mtr-Temp",
    ),
    divergence_slit_1_m=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 1 right",
        motorpv="BIFROST-DivSl1:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_1_m_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Divergence slit 1 right temperature",
        readpv="BIFROST-DivSl1:MC-SlYm-01:Mtr-Temp",
    ),
    divergence_slit_1=device(
        "nicos.devices.generic.slit.HorizontalGap",
        description="Divergence slit 1 abstraction device",
        opmode="2blades",
        coordinates="equal",
        left="divergence_slit_1_m",
        right="divergence_slit_1_p",
    ),
    divergence_slit_2_p=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 2 left",
        motorpv="BIFROST-DivSl2:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_2_p_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Divergence slit 2 left temperature",
        readpv="BIFROST-DivSl2:MC-SlYp-01:Mtr-Temp",
    ),
    divergence_slit_2_m=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 2 right",
        motorpv="BIFROST-DivSl2:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_2_m_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Divergence slit 2 right temperature",
        readpv="BIFROST-DivSl2:MC-SlYm-01:Mtr-Temp",
    ),
    divergence_slit_2=device(
        "nicos.devices.generic.slit.HorizontalGap",
        description="Divergence slit 2 abstraction device",
        opmode="2blades",
        coordinates="equal",
        left="divergence_slit_2_m",
        right="divergence_slit_2_p",
    ),
    divergence_slit_3_p=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 3 left",
        motorpv="BIFROST-DivSl3:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_3_p_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Divergence slit 3 left temperature",
        readpv="BIFROST-DivSl3:MC-SlYp-01:Mtr-Temp",
    ),
    divergence_slit_3_m=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Divergence slit 3 right",
        motorpv="BIFROST-DivSl3:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    divergence_slit_3_m_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Divergence slit 3 right temperature",
        readpv="BIFROST-DivSl3:MC-SlYm-01:Mtr-Temp",
    ),
    divergence_slit_3=device(
        "nicos.devices.generic.slit.HorizontalGap",
        description="Divergence slit 3 abstraction device",
        opmode="2blades",
        coordinates="equal",
        left="divergence_slit_3_m",
        right="divergence_slit_3_p",
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
