description = "Motors for the detector arm"

det_arm_root = "ESTIA-DtCpl:MC-Pne-01"

devices = dict(
    detector_rot=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector Motion System (Z-Rotation)",
        motorpv="ESTIA-DtRot:MC-RotZ01:Mtr",
    ),
    detector_arm=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Detector Arm Pneumatic Coupling: Support Structure on Air Pads",
        writepv=f"{det_arm_root}:ShtOpen",
        readpv=f"{det_arm_root}:ShtAuxBits07",
        resetpv=f"{det_arm_root}:ShtErrRst",
        msgtxt=f"{det_arm_root}:ShtMsgTxt",
    ),
)
