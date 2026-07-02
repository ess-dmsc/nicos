description = "NMX Pinhole Exchanger (Collimation System)"

pv_root = "NMX"
pinhole_pv_root= f"{pv_root}-PinChg:"
aux_pv_root= f"{pv_root}-ApChg:"
raise_pv_root= f"{aux_pv_root}MC-Pne-01:"
arm_pv_root= f"{aux_pv_root}MC-Pne-02:"

pin_options = {f"Pinhole {i}": i for i in range(11)}
pin_options['No pinhole (unmount)'] = 11

devices = dict(
    # Pinhole main controls
    pinhole__mount_pin=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="Mount a selected pinhole (or have no pinhole mounted)",
        readpv=f"{pinhole_pv_root}MC-Pin-01:Mtr.RBV",
        writepv=f"{pinhole_pv_root}MC-Pin-01:Mtr.VAL",
        mapping=pin_options, # Value "11" unmounts. TODO: Add all pins.
        fmtstr="%d",
    ),
    pinhole__current_pin=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Pinhole current mounted pin",
        readpv=f"{pinhole_pv_root}MC-Pin-01:Mtr.RBV",
        fmtstr="%d",
    ),
    pinhole_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Pinhole status",
        pv_root="NMX-PinChg:MC-Pin-01:Mtr",
        number_of_bits=26,
        bitname_prefix="-NamAuxBit",
    ),
    # Auxiliary motor controls (for calibration)
    pinhole__motor=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole exchanger (as a motor)",
        motorpv=f"{pinhole_pv_root}MC-Pin-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    pinhole__carousel_rotation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole exchanger carousel rotation",
        motorpv=f"{aux_pv_root}MC-RotZ-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    pinhole__carousel_electromagnet=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole exchanger carousel electromagnet",
        motorpv=f"{aux_pv_root}MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    pinhole__carousel_v_raise=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Pinhole exchanger carousel vertical raise (pneumatic)",
        writepv=f"{raise_pv_root}ShtOpen",
        readpv=f"{raise_pv_root}ShtAuxBits07",
        resetpv=f"{raise_pv_root}ShtErrRst",
        msgtxt=f"{raise_pv_root}ShtMsgTxt",
        visibility={},
    ),
    pinhole__aperture_arm=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Pinhole exchanger aperture arm (pneumatic)",
        writepv=f"{arm_pv_root}ShtOpen",
        readpv=f"{arm_pv_root}ShtAuxBits07",
        resetpv=f"{arm_pv_root}ShtErrRst",
        msgtxt=f"{arm_pv_root}ShtMsgTxt",
        visibility={},
    ),

)
