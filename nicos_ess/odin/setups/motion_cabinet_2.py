# ODIN — Motion cabinet 2

description = "Motion cabinet 2"

devices = dict(
    # --- Pneumatics: Pinhole graphite diffuser & filters + experiment shutter ---
    pinhole_diffuser=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Pinhole: Graphite Diffuser",
        writepv="ODIN-PinDif:MC-Pne-01:ShtOpen",
        readpv="ODIN-PinDif:MC-Pne-01:ShtAuxBits07",
        resetpv="ODIN-PinDif:MC-Pne-01:ShtErrRst",
    ),
    pinhole_diffuser_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the pinhole graphite diffuser",
        readpv="ODIN-PinDif:MC-Pne-01:ShtMsgTxt",
    ),
    pinhole_filter_1=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Pinhole: Filter 1",
        writepv="ODIN-PinFil:MC-Pne-01:ShtOpen",
        readpv="ODIN-PinFil:MC-Pne-01:ShtAuxBits07",
        resetpv="ODIN-PinFil:MC-Pne-01:ShtErrRst",
    ),
    pinhole_filter_1_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of pinhole filter 1",
        readpv="ODIN-PinFil:MC-Pne-01:ShtMsgTxt",
    ),
    pinhole_filter_2=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Pinhole: Filter 2",
        writepv="ODIN-PinFil:MC-Pne-02:ShtOpen",
        readpv="ODIN-PinFil:MC-Pne-02:ShtAuxBits07",
        resetpv="ODIN-PinFil:MC-Pne-02:ShtErrRst",
    ),
    pinhole_filter_2_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of pinhole filter 2",
        readpv="ODIN-PinFil:MC-Pne-02:ShtMsgTxt",
    ),
    pinhole_filter_3=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Pinhole: Filter 3",
        writepv="ODIN-PinFil:MC-Pne-03:ShtOpen",
        readpv="ODIN-PinFil:MC-Pne-03:ShtAuxBits07",
        resetpv="ODIN-PinFil:MC-Pne-03:ShtErrRst",
    ),
    pinhole_filter_3_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of pinhole filter 3",
        readpv="ODIN-PinFil:MC-Pne-03:ShtMsgTxt",
    ),
    experiment_shutter=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Experiment Shutter",
        writepv="ODIN-ExSht:MC-Pne-01:ShtOpen",
        readpv="ODIN-ExSht:MC-Pne-01:ShtAuxBits07",
        resetpv="ODIN-ExSht:MC-Pne-01:ShtErrRst",
    ),
    experiment_shutter_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the experiment shutter",
        readpv="ODIN-ExSht:MC-Pne-01:ShtMsgTxt",
    ),
    # --- Motors: Pinhole slit sets 1 & 2 ---
    pinhole_1_yp=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole Slit 1 left (Y+)",
        motorpv="ODIN-PinSl1:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    pinhole_1_ym=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole Slit 1 right (Y-)",
        motorpv="ODIN-PinSl1:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    pinhole_1_zp=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole Slit 1 upper (Z+)",
        motorpv="ODIN-PinSl1:MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    pinhole_1_zm=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole Slit 1 lower (Z-)",
        motorpv="ODIN-PinSl1:MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    pinhole_1_hori=device(
        "nicos.devices.generic.slit.HorizontalGap",
        description="Pinhole Slit 1 horizontal gap abstraction device",
        opmode="2blades",
        coordinates="equal",
        left="pinhole_1_ym",
        right="pinhole_1_yp",
    ),
    pinhole_1_vert=device(
        "nicos.devices.generic.slit.VerticalGap",
        description="Pinhole Slit 1 vertical gap abstraction device",
        opmode="2blades",
        coordinates="equal",
        bottom="pinhole_1_zm",
        top="pinhole_1_zp",
    ),
    pinhole_2_yp=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole Slit 2 left (Y+)",
        motorpv="ODIN-PinSl2:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    pinhole_2_ym=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole Slit 2 right (Y-)",
        motorpv="ODIN-PinSl2:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    pinhole_2_zp=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole Slit 2 upper (Z+)",
        motorpv="ODIN-PinSl2:MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    pinhole_2_zm=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole Slit 2 lower (Z-)",
        motorpv="ODIN-PinSl2:MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    pinhole_2_hori=device(
        "nicos.devices.generic.slit.HorizontalGap",
        description="Pinhole Slit 2 horizontal gap abstraction device",
        opmode="2blades",
        coordinates="equal",
        left="pinhole_2_ym",
        right="pinhole_2_yp",
    ),
    pinhole_2_vert=device(
        "nicos.devices.generic.slit.VerticalGap",
        description="Pinhole Slit 2 vertical gap abstraction device",
        opmode="2blades",
        coordinates="equal",
        bottom="pinhole_2_zm",
        top="pinhole_2_zp",
    ),
    # --- Cabinet health ---
    cabinet_2_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 2 status",
        pv_root="ODIN-MCS2:MC-MCU-02:Cabinet",
        number_of_bits=24,
    ),
    cabinet_2_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 2 pressure 1",
        readpv="ODIN-MCS2:MC-MCU-02:Pressure1",
    ),
    cabinet_2_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 2 pressure 2",
        readpv="ODIN-MCS2:MC-MCU-02:Pressure2",
    ),
)
