description = "TOF counter devices"

group = "lowlevel"

devices = dict(
    monitor=device(
        "nicos.devices.generic.VirtualCounter",
        description="TOFTOF monitor",
        fmtstr="%d",
        type="monitor",
        visibility=(),
        pollinterval=None,
    ),
    timer=device(
        "nicos.devices.generic.VirtualTimer",
        description="TOFTOF timer",
        fmtstr="%.2f",
        unit="s",
        visibility=(),
        pollinterval=None,
    ),
    image=device(
        "nicos_mlz.toftof.devices.VirtualImage",
        description="Image data device",
        fmtstr="%d",
        pollinterval=None,
        visibility=(),
        numinputs=1006,
        size=(1024, 1024),
        datafile="nicos_demo/vtoftof/data/test/data.npz",
    ),
    det=device(
        "nicos_mlz.toftof.devices.Detector",
        description="The TOFTOF detector device",
        timers=["timer"],
        monitors=["monitor"],
        images=["image"],
        rc="rc",
        chopper="ch",
        chdelay="chdelay",
        maxage=3,
        pollinterval=None,
        liveinterval=10.0,
        saveintervals=[30.0],
        detinfofile="nicos_demo/vtoftof/detinfo.dat",
    ),
)
