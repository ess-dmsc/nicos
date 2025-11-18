description = "Motors for the metrology cart"

pv_approach = "ESTIA-SG1Ct:MC-RotZ-01:Mtr"
pv_position = "ESTIA-SG1Ct:MC-LinX-01:Mtr"

devices = dict(
    mapproach=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rotator for approach",
        motorpv=pv_approach,
        powerautopv=f"{pv_approach}-PwrAuto",
        errormsgpv=f"{pv_approach}-MsgTxt",
        errorbitpv=f"{pv_approach}-Err",
        reseterrorpv=f"{pv_approach}-ErrRst",
        temppv=f"{pv_approach}-Temp",
    ),
    mpos=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Cart positioning",
        motorpv=pv_position,
        powerautopv=f"{pv_position}-PwrAuto",
        errormsgpv=f"{pv_position}-MsgTxt",
        errorbitpv=f"{pv_position}-Err",
        reseterrorpv=f"{pv_position}-ErrRst",
        temppv=f"{pv_position}-Temp",
    ),
    mcart=device(
        "nicos.devices.generic.sequence.LockedDevice",
        description="Metrology Cart device",
        device="mpos",
        lock="mapproach",
        unlockvalue=60.0,
        lockvalue=180.0,
    ),
)
