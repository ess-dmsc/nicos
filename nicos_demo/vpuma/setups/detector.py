description = "common detector devices provided by QMesyDAQ"

group = "lowlevel"

devices = dict(
    timer=device(
        "nicos.devices.generic.VirtualTimer",
        description="QMesyDAQ timer",
        visibility=(),
        unit="s",
        fmtstr="%.1f",
    ),
    mon1=device(
        "nicos.devices.generic.VirtualCounter",
        description="QMesyDAQ monitor 1",
        type="monitor",
        visibility=(),
        fmtstr="%d",
    ),
    # mon2 = device('nicos.devices.generic.VirtualCounter',
    #     type = 'monitor',
    #     visibility = (),
    #     fmtstr = '%d',
    # ),
    det1=device(
        "nicos.devices.generic.VirtualCounter",
        type="counter",
        visibility=(),
        fmtstr="%d",
    ),
    det2=device(
        "nicos.devices.generic.VirtualCounter",
        type="counter",
        visibility=(),
        fmtstr="%d",
    ),
    det3=device(
        "nicos.devices.generic.VirtualCounter",
        type="counter",
        visibility=(),
        fmtstr="%d",
    ),
    # det4 = device('nicos.devices.generic.VirtualCounter',
    #     type = 'counter',
    #     visibility = (),
    #     fmtstr = '%d',
    # ),
    # det5 = device('nicos.devices.generic.VirtualCounter',
    #     type = 'counter',
    #     visibility = (),
    #     fmtstr = '%d',
    # ),
    events=device(
        "nicos.devices.generic.VirtualCounter",
        description="QMesyDAQ Events channel",
        type="counter",
        visibility=(),
        fmtstr="%d",
    ),
    image=device(
        "nicos.devices.generic.VirtualImage",
        description="QMesyDAQ Image",
        fmtstr="%d",
        pollinterval=86400,
        size=(1, 5),
        visibility=(),
    ),
    det=device(
        "nicos.devices.generic.Detector",
        # description = 'Puma detector device (5 counters)',
        description="Puma detector QMesydaq device (3 counters)",
        timers=["timer"],
        # monitors = ['mon1', 'mon2'],
        monitors=["mon1"],
        # counters = ['det1', 'det2', 'det3', 'det4', 'det5'],
        counters=["det1", "det2", "det3"],
        images=[],
        maxage=1,
        pollinterval=1,
    ),
)

startupcode = """
SetDetectors(det)
"""
