description = "Motors for the metrology cart"

pvprefix = "ESTIA-Sel2:MC-MCU-01:"

group = "lowlevel"

devices = dict(
    mpos2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        motorpv=f"{pvprefix}Mtr12",
        powerautopv=f"{pvprefix}Mtr12-PwrAuto",
        errormsgpv=f"{pvprefix}Mtr12-MsgTxt",
        errorbitpv=f"{pvprefix}Mtr12-Err",
        reseterrorpv=f"{pvprefix}Mtr12-ErrRst",
        temppv=f"{pvprefix}Mtr12-Temp",
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    mapproach2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        motorpv=f"{pvprefix}Mtr13",
        powerautopv=f"{pvprefix}Mtr13-PwrAuto",
        errormsgpv=f"{pvprefix}Mtr13-MsgTxt",
        errorbitpv=f"{pvprefix}Mtr13-Err",
        reseterrorpv=f"{pvprefix}Mtr13-ErrRst",
        temppv=f"{pvprefix}Mtr13-Temp",
        unit="deg",
        fmtstr="%.1f",
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    mcart2=device(
        "nicos.devices.generic.sequence.LockedDevice",
        device="mpos2",
        lock="mapproach2",
        unlockvalue=1.0,
        lockvalue=90.0,
    ),
)
