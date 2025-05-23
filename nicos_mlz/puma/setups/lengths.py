description = "Collimation and Lengths"
group = "lowlevel"

includes = ["system"]

# !!! keep in sync with nicos_mlz/puma/devices/spectro.py !!!

devices = dict(
    lsm=device(
        "nicos.devices.generic.ManualMove",
        description="distance source - mono",
        default=5633,
        unit="mm",
        fmtstr="%.0f",
        abslimits=(5633, 5633),
        visibility={
            "metadata",
        },
    ),
    lms=device(
        "nicos.devices.generic.ManualMove",
        description="distance mono - sample",
        default=2090,
        unit="mm",
        fmtstr="%.0f",
        abslimits=(2090, 2100),
        visibility={
            "metadata",
        },
    ),
    lsa=device(
        "nicos.devices.generic.ManualMove",
        description="distance sample - ana",
        default=910,
        unit="mm",
        fmtstr="%.0f",
        abslimits=(900, 1900),
        visibility={
            "metadata",
        },
    ),
    lad=device(
        "nicos.devices.generic.ManualMove",
        description="distance ana - detector",
        default=750,
        unit="mm",
        fmtstr="%.0f",
        abslimits=(500, 1000),
        visibility={
            "metadata",
        },
    ),
    vs=device(
        "nicos.devices.generic.TwoAxisSlit",
        description="virtual source",
        horizontal=device(
            "nicos.devices.generic.Axis",
            motor=device(
                "nicos.devices.generic.VirtualMotor",
                curvalue=78,
                unit="mm",
                fmtstr="%.1f",
                abslimits=(78, 78),
            ),
            precision=0,
            visibility={
                "metadata",
            },
        ),
        vertical=device(
            "nicos.devices.generic.Axis",
            motor=device(
                "nicos.devices.generic.VirtualMotor",
                curvalue=150,
                unit="mm",
                fmtstr="%.1f",
                abslimits=(150, 150),
            ),
            precision=0,
            visibility={
                "metadata",
            },
        ),
        visibility=(),
    ),
    cb1=device(
        "nicos.devices.generic.ManualMove",
        description="vertical divergence before mono",
        default=240,
        unit="min",
        fmtstr="%6.1f",
        abslimits=(240, 240),
        visibility=(),
    ),
    cb2=device(
        "nicos.devices.generic.ManualMove",
        description="vertical divergence after mono",
        default=240,
        unit="min",
        fmtstr="%6.1f",
        abslimits=(240, 240),
        visibility=(),
    ),
    cb3=device(
        "nicos.devices.generic.ManualMove",
        description="vertical divergence before ana",
        default=240,
        unit="min",
        fmtstr="%6.1f",
        abslimits=(240, 240),
        visibility=(),
    ),
    cb4=device(
        "nicos.devices.generic.ManualMove",
        description="vertical divergence after ana",
        default=240,
        unit="min",
        fmtstr="%6.1f",
        abslimits=(240, 240),
        visibility=(),
    ),
    ca1=device(
        "nicos.devices.generic.ManualSwitch",
        description="monochromator collimator before mono",
        states=["none", "20m", "40m", "60m"],
        visibility=(),
    ),
    ca2=device(
        "nicos.devices.generic.ManualSwitch",
        description="post monochromator collimator",
        states=["none", "14m", "20m", "24m", "30m", "45m", "60m"],
        visibility=(),
    ),
    ca3=device(
        "nicos.devices.generic.ManualSwitch",
        description="pre analyser collimator",
        states=["none", "20m", "30m", "45m", "60m", "120m"],
        visibility=(),
    ),
    ca4=device(
        "nicos.devices.generic.ManualSwitch",
        description="post analyser collimator",
        states=["none", "10m", "30m", "45m", "60m"],
        visibility=(),
    ),
)
