description = "Test detector ymir"

devices = dict(
    timer=device(
        "nicos.devices.generic.VirtualTimer",
        description="Simulated TIM1",
        fmtstr="%.2f",
        unit="s",
    ),
    pulse_counter=device(
        "nicos_ess.devices.epics.pulse_counter.PulseCounter",
        description="EVR Pulse Counter",
        readpv="YMIR-TS:Ctrl-EVR-01:EvtACnt-I",
        fmtstr="%d",
    ),
    detector=device(
        "nicos.devices.generic.Detector",
        description="Classical detector with single channels",
        timers=["timer"],
        counters=["pulse_counter"],
        maxage=86400,
        pollinterval=None,
    ),
)

startupcode = """
SetDetectors(detector)
"""
