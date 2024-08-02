description = "Devices from Motor Rack 12"

pvprefix = "SQ:SANS-LLB:rack12:"

devices = dict(
    sl5yp=device(
        "nicos.devices.epics.pyepics.motor.HomingProtectedEpicsMotor",
        epicstimeout=3.0,
        description="Slit 5 down",
        motorpv=pvprefix + "sl5yp",
        errormsgpv=pvprefix + "sl5yp-MsgTxt",
        precision=0.01,
    ),
    sl5yn=device(
        "nicos.devices.epics.pyepics.motor.HomingProtectedEpicsMotor",
        epicstimeout=3.0,
        description="Slit 5 up",
        motorpv=pvprefix + "sl5yn",
        errormsgpv=pvprefix + "sl5yn-MsgTxt",
        precision=0.01,
    ),
    sl5xp=device(
        "nicos.devices.epics.pyepics.motor.HomingProtectedEpicsMotor",
        epicstimeout=3.0,
        description="Slit 5 left",
        motorpv=pvprefix + "sl5xp",
        errormsgpv=pvprefix + "sl5xp-MsgTxt",
        precision=0.01,
    ),
    sl5xn=device(
        "nicos.devices.epics.pyepics.motor.HomingProtectedEpicsMotor",
        epicstimeout=3.0,
        description="Slit 5 right",
        motorpv=pvprefix + "sl5xn",
        errormsgpv=pvprefix + "sl5xn-MsgTxt",
        precision=0.01,
    ),
    guide5pos=device(
        "nicos.devices.epics.pyepics.motor.HomingProtectedEpicsMotor",
        epicstimeout=3.0,
        description="Guide 5  translation",
        motorpv=pvprefix + "guide5",
        errormsgpv=pvprefix + "guide5-MsgTxt",
        precision=0.01,
    ),
    guide5=device(
        "nicos.devices.generic.switcher.Switcher",
        description="Guide 5 choice",
        moveable="guide5pos",
        mapping={
            "out": 10,
            "in": 100,
        },
        precision=0.1,
        blockingmove=True,
    ),
    slit5=device(
        "nicos.devices.generic.slit.Slit",
        description="Slit 3 with left, right, bottom and top motors",
        opmode="4blades",
        coordinates="opposite",
        left="sl5xp",
        right="sl5xn",
        top="sl5yp",
        bottom="sl5yn",
        visibility=(),
    ),
    sl5xw=device(
        "nicos.core.device.DeviceAlias",
        description="slit  5 width",
        alias="slit5.width",
        devclass="nicos.devices.generic.slit.WidthSlitAxis",
    ),
    sl5xc=device(
        "nicos_sinq.sans-llb.devices.slit.InvertedXSlitAxis",
        description="slit 5 x center position",
        slit="slit5",
        unit="mm",
    ),
    sl5yw=device(
        "nicos.core.device.DeviceAlias",
        description="slit 5 height",
        alias="slit5.height",
        devclass="nicos.devices.generic.slit.HeightSlitAxis",
    ),
    sl5yc=device(
        "nicos.core.device.DeviceAlias",
        description="slit 5 y center position",
        alias="slit5.centery",
        devclass="nicos.devices.generic.slit.CenterYSlitAxis",
    ),
    sl6yp=device(
        "nicos.devices.epics.pyepics.motor.HomingProtectedEpicsMotor",
        epicstimeout=3.0,
        description="Slit 6 down",
        motorpv=pvprefix + "sl6yp",
        errormsgpv=pvprefix + "sl6yp-MsgTxt",
        precision=0.01,
    ),
    sl6yn=device(
        "nicos.devices.epics.pyepics.motor.HomingProtectedEpicsMotor",
        epicstimeout=3.0,
        description="Slit 6 up",
        motorpv=pvprefix + "sl6yn",
        errormsgpv=pvprefix + "sl6yn-MsgTxt",
        precision=0.01,
    ),
    sl6xp=device(
        "nicos.devices.epics.pyepics.motor.HomingProtectedEpicsMotor",
        epicstimeout=3.0,
        description="Slit 6 left",
        motorpv=pvprefix + "sl6xp",
        errormsgpv=pvprefix + "sl6xp-MsgTxt",
        precision=0.01,
    ),
    sl6xn=device(
        "nicos.devices.epics.pyepics.motor.HomingProtectedEpicsMotor",
        epicstimeout=3.0,
        description="Slit 6 right",
        motorpv=pvprefix + "sl6xn",
        errormsgpv=pvprefix + "sl6xn-MsgTxt",
        precision=0.01,
    ),
    slit6=device(
        "nicos.devices.generic.slit.Slit",
        description="Slit 3 with left, right, bottom and top motors",
        opmode="4blades",
        coordinates="opposite",
        left="sl6xp",
        right="sl6xn",
        top="sl6yp",
        bottom="sl6yn",
        visibility=(),
    ),
    sl6xw=device(
        "nicos.core.device.DeviceAlias",
        description="slit  6 width",
        alias="slit6.width",
        devclass="nicos.devices.generic.slit.WidthSlitAxis",
    ),
    sl6xc=device(
        "nicos_sinq.sans-llb.devices.slit.InvertedXSlitAxis",
        description="slit 6 x center position",
        slit="slit6",
        unit="mm",
    ),
    sl6yw=device(
        "nicos.core.device.DeviceAlias",
        description="slit 6 height",
        alias="slit6.height",
        devclass="nicos.devices.generic.slit.HeightSlitAxis",
    ),
    sl6yc=device(
        "nicos.core.device.DeviceAlias",
        description="slit 6 y center position",
        alias="slit6.centery",
        devclass="nicos.devices.generic.slit.CenterYSlitAxis",
    ),
    sl6_distance=device(
        "nicos.devices.generic.ManualMove",
        description="distance sample slit6",
        abslimits=(100, 500),
        unit="mm",
    ),
)
startupcode = """
sl5xw.alias='slit5.width'
sl5yw.alias='slit5.height'
sl5yc.alias='slit5.centery'
sl6xw.alias='slit6.width'
sl6yw.alias='slit6.height'
sl6yc.alias='slit6.centery'
"""
