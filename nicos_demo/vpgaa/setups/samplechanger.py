description = "sample table devices"

group = "lowlevel"

devices = dict(
    samplemotor=device(
        "nicos.devices.generic.VirtualMotor",
        description="Motor to change the sample position",
        abslimits=(1, 16),
        speed=0.1,
        unit="Pos",
        curvalue=1,
        visibility=(),
        fmtstr="%.1f",
    ),
    pushactuator=device(
        "nicos.devices.generic.ManualSwitch",
        description="Push sample up and down",
        states=["up", "down"],
        fmtstr="%d",
        visibility=(),
    ),
    sensort=device(
        "nicos_demo.vpgaa.devices.PushReader",
        moveable="pushactuator",
        inverse=True,
        visibility=(),
    ),
    sensorl=device(
        "nicos_demo.vpgaa.devices.PushReader",
        moveable="pushactuator",
        visibility=(),
    ),
    push=device(
        "nicos_mlz.pgaa.devices.SamplePusher",
        description="Push sample up and down",
        unit="",
        actuator="pushactuator",
        sensort="sensort",
        sensorl="sensorl",
    ),
    sc=device(
        "nicos_mlz.pgaa.devices.SampleChanger",
        description="The sample changer",
        motor="samplemotor",
        push="push",
    ),
)
