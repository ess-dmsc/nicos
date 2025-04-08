description = "Test detector ymir"

devices = dict(
    # mon=device(
    #     "nicos.devices.generic.VirtualCounter",
    #     description="Simulated MON1",
    #     fmtstr="%d",
    #     type="monitor",
    # ),
    counter=device(
        "nicos.devices.generic.DeviceAlias",
        devclass="nicos.devices.generic.PassiveChannel",
    ),
    timer=device(
        "nicos.devices.generic.VirtualTimer",
        description="Simulated TIM1",
        fmtstr="%.2f",
        unit="s",
    ),
    detector=device(
        "nicos.devices.generic.Detector",
        description="Classical detector with single channels",
        timers=["tim1"],
        counters=["counter"],
        # monitors=["mon"],
        maxage=86400,
        pollinterval=None,
    ),
)

startupcode = """
SetDetectors(detector)
"""
