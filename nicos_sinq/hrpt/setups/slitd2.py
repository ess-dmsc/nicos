description = "Slit 2 devices in the SINQ HRPT."

pvprefix = "SQ:HRPT:mote:"

devices = dict(
    brle=device(
        "nicos.devices.epics.pyepics.motor.EpicsMotor",
        description="Slit 2 left motor",
        motorpv=pvprefix + "BRLE",
        errormsgpv=pvprefix + "BRLE-MsgTxt",
        precision=0.01,
    ),
    brri=device(
        "nicos.devices.epics.pyepics.motor.EpicsMotor",
        description="Slit 2 right motor",
        motorpv=pvprefix + "BRRI",
        errormsgpv=pvprefix + "BRRI-MsgTxt",
        precision=0.01,
    ),
    brto=device(
        "nicos.devices.epics.pyepics.motor.EpicsMotor",
        description="Slit 2 top motor",
        motorpv=pvprefix + "BRTO",
        errormsgpv=pvprefix + "BRTO-MsgTxt",
        precision=0.01,
    ),
    brbo=device(
        "nicos.devices.epics.pyepics.motor.EpicsMotor",
        description="Slit 2 bottom motor",
        motorpv=pvprefix + "BRBO",
        errormsgpv=pvprefix + "BRBO-MsgTxt",
        precision=0.01,
    ),
    slit2=device(
        "nicos_sinq.hrpt.devices.brslit.BRSlit",
        description="Slit 2 with left, right, bottom and top motors",
        left="brle",
        top="brto",
        bottom="brbo",
        right="brri",
        visibility=(),
    ),
)
