# ODIN — Motion cabinet 1

description = "Motion cabinet 1"

devices = dict(
    # --- Pneumatic: Heavy shutter ---
    heavy_shutter=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Heavy Shutter",
        writepv="ODIN-HvSht:MC-Pne-01:ShtOpen",
        readpv="ODIN-HvSht:MC-Pne-01:ShtAuxBits07",
        resetpv="ODIN-HvSht:MC-Pne-01:ShtErrRst",
    ),
    heavy_shutter_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the heavy shutter",
        readpv="ODIN-HvSht:MC-Pne-01:ShtMsgTxt",
    ),
    # --- Motor: WFMC translation stage ---
    wfmc_translation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Bunker 1 WFMC Translation Stage (Z)",
        motorpv="ODIN-ChpLin:MC-LinX-01:Mtr",
        monitor_deadband=0.01,
    ),
    # --- Cabinet health ---
    cabinet_1_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 1 status",
        pv_root="ODIN-MCS1:MC-MCU-01:Cabinet",
        number_of_bits=24,
    ),
    cabinet_1_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 1",
        readpv="ODIN-MCS1:MC-MCU-01:Pressure1",
    ),
    cabinet_1_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 2",
        readpv="ODIN-MCS1:MC-MCU-01:Pressure2",
    ),
)
