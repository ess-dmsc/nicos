description = "standard detector and counter card"
group = "lowlevel"

includes = ["base"]

tango_base = "tango://miractrl.mira.frm2.tum.de:10000/mira/"

devices = dict(
    timer=device(
        "nicos.devices.entangle.TimerChannel",
        tangodevice=tango_base + "frmctr/timer",
        fmtstr="%.2f",
        visibility=(),
    ),
    mon1=device(
        "nicos.devices.entangle.CounterChannel",
        tangodevice=tango_base + "frmctr/ctr0",
        type="monitor",
        fmtstr="%d",
        visibility=(),
    ),
    mon2=device(
        "nicos.devices.entangle.CounterChannel",
        tangodevice=tango_base + "frmctr/ctr1",
        type="monitor",
        fmtstr="%d",
        visibility=(),
    ),
    ctr1=device(
        "nicos.devices.entangle.CounterChannel",
        tangodevice=tango_base + "frmctr/ctr2",
        type="counter",
        fmtstr="%d",
        visibility=(),
    ),
    ctr2=device(
        "nicos.devices.entangle.CounterChannel",
        tangodevice=tango_base + "frmctr/ctr3",
        type="counter",
        fmtstr="%d",
        visibility=(),
    ),
    det=device(
        "nicos.devices.generic.Detector",
        description="FRM II multichannel counter card",
        timers=["timer"],
        monitors=["mon1", "mon2"],
        counters=["ctr1", "ctr2"],
        fmtstr="timer %s, mon1 %s, mon2 %s, ctr1 %s, ctr2 %s",
        maxage=2,
        pollinterval=0.5,
    ),
    det_fore=device(
        "nicos.devices.generic.DetectorForecast",
        description="forecast for det values",
        pollinterval=0.5,
        maxage=2,
        unit="",
        det="det",
    ),
    DetHV=device(
        "nicos.devices.entangle.Actuator",
        description="HV supply for single tube detector (usual value 850 V)",
        tangodevice=tango_base + "detectorhv/voltage",
        warnlimits=(840, 860),
        pollinterval=10,
        maxage=20,
        fmtstr="%d",
    ),
    MonHV=device(
        "nicos.devices.entangle.Actuator",
        description="HV supply for monitor counter (usual value 500 V)",
        tangodevice=tango_base + "monitorhv/voltage",
        warnlimits=(490, 510),
        pollinterval=10,
        maxage=30,
        fmtstr="%d",
    ),
    VetoHV=device(
        "nicos.devices.entangle.PowerSupply",
        description="Veto HV power supply (usual value 500 V)",
        tangodevice=tango_base + "vetohv/voltage",
        fmtstr="%d",
        pollinterval=10,
        maxage=21,
    ),
)
