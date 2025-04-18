description = "sample table devices"

group = "lowlevel"

excludes = ["robot"]

tangobase = "tango://motorbox02.stressi.frm2.tum.de:10000/box/"

devices = dict(
    tths_m=device(
        "nicos.devices.entangle.Motor",
        description="TTHS motor",
        tangodevice=tangobase + "channel1/motor",
        visibility=(),
    ),
    tths_c=device(
        "nicos.devices.entangle.Sensor",
        description="TTHS coder",
        tangodevice=tangobase + "channel1/coder",
        visibility=(),
    ),
    tths=device(
        "nicos.devices.generic.Axis",
        description="TTHS",
        motor="tths_m",
        coder="tths_c",
        precision=0.01,
    ),
    omgs_m=device(
        "nicos.devices.entangle.Motor",
        description="OMGS motor",
        tangodevice=tangobase + "channel2/motor",
        visibility=(),
    ),
    omgs_c=device(
        "nicos.devices.entangle.Sensor",
        description="OMGS coder",
        tangodevice=tangobase + "channel2/coder",
        visibility=(),
    ),
    omgs=device(
        "nicos.devices.generic.Axis",
        description="OMGS",
        motor="omgs_m",
        coder="omgs_c",
        precision=0.01,
    ),
    xt_m=device(
        "nicos.devices.entangle.Motor",
        description="XT motor",
        tangodevice=tangobase + "channel5/motor",
        visibility=(),
    ),
    xt_c=device(
        "nicos.devices.entangle.Sensor",
        description="XT coder",
        tangodevice=tangobase + "channel5/coder",
        visibility=(),
    ),
    xt=device(
        "nicos.devices.generic.Axis",
        description="XT",
        motor="xt_m",
        coder="xt_c",
        precision=0.01,
    ),
    yt_m=device(
        "nicos.devices.entangle.Motor",
        description="YT motor",
        tangodevice=tangobase + "channel6/motor",
        visibility=(),
    ),
    yt_c=device(
        "nicos.devices.entangle.Sensor",
        description="YT coder",
        tangodevice=tangobase + "channel6/coder",
        visibility=(),
    ),
    yt=device(
        "nicos.devices.generic.Axis",
        description="YT",
        motor="yt_m",
        coder="yt_c",
        precision=0.01,
    ),
    zt_m=device(
        "nicos.devices.entangle.Motor",
        description="ZT motor",
        tangodevice=tangobase + "channel7/motor",
        visibility=(),
    ),
    zt_c=device(
        "nicos.devices.entangle.Sensor",
        description="ZT coder",
        tangodevice=tangobase + "channel7/coder",
        visibility=(),
    ),
    zt=device(
        "nicos.devices.generic.Axis",
        description="ZT",
        motor="zt_m",
        coder="zt_c",
        precision=0.01,
    ),
)
