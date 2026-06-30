description = "NMX Pinhole Exchanger (Collimation System)"

pv_root = "NMX"
pinhole_pv_root= f"{pv_root}-PinChg:"
aux_pv_root= f"{pv_root}-ApChg:"
raise_pv_root= f"{aux_pv_root}MC-Pne-01:"
arm_pv_root= f"{aux_pv_root}MC-Pne-02:"

# TODO: Check descriptions (axis and cabinet numbers)!

devices = dict(
    # Pinhole
    pinhole__mount_pin=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="Mount a selected pinhole (or have no pinhole mounted)",
        readpv=f"{pinhole_pv_root}MC-Pin-01:Mtr.RBV",
        writepv=f"{pinhole_pv_root}MC-Pin-01:Mtr.VAL",
        mapping={"Pinhole 0": 0, "Pinhole 1": 1, "Pinhole 2": 2, "Pinhole 3": 3, "No pinhole (unmount)": 11}, # Value "11" unmounts. TODO: Add all pins.
        fmtstr="%d",
    ),
    pinhole__current_pin=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Pinhole current mounted pin",
        readpv=f"{pinhole_pv_root}MC-Pin-01:Mtr.RBV",
    ),
    pinhole__motor=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole exchanger (as a motor)",
        motorpv=f"{pinhole_pv_root}MC-Pin-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    # Bits: B0..B19
    # TODO: Find a better device for this!
    #pinhole__current_pinhole=device(
    #    "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
    #    description="Pinhole exchanger mounted pin",
    #    pv_root=f"{pinhole_pv_root}MC-Pin-01:Mtr-StatusBits",
    #    number_of_bits=11,
    #),
    pinhole__status_bit0=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Pinhole status bit 0",
        readpv=f"{pinhole_pv_root}MC-Pin-01:Mtr-StatusBits.B0",
        fmtstr="%d",
    ),
    pinhole__status_bit1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Pinhole status bit 1",
        readpv=f"{pinhole_pv_root}MC-Pin-01:Mtr-StatusBits.B1",
        fmtstr="%d",
    ),
    # Auxiliary motor controls (for calibration)
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
