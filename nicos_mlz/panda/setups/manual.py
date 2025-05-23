description = "collimators and lengths"

group = "lowlevel"
display_order = 10

devices = dict(
    lsm=device(
        "nicos.devices.generic.ManualMove",
        description="distance source - mono",
        default=7800,
        unit="mm",
        fmtstr="%.0f",
        abslimits=(7800, 7800),
    ),
    lms=device(
        "nicos.devices.generic.ManualMove",
        description="distance mono - sample",
        default=2100,
        unit="mm",
        fmtstr="%.0f",
        abslimits=(2050, 2200),
    ),
    lsa=device(
        "nicos.devices.generic.ManualMove",
        description="distance sample - ana",
        default=940,
        unit="mm",
        fmtstr="%.0f",
        abslimits=(850, 1550),
    ),
    lad=device(
        "nicos.devices.generic.ManualMove",
        description="distance ana - detector",
        default=940,
        unit="mm",
        fmtstr="%.0f",
        abslimits=(800, 1550),
    ),
    cb1=device(
        "nicos.devices.generic.ManualMove",
        description="vertical divergence before mono",
        default=800,
        unit="min",
        fmtstr="%6.1f",
        abslimits=(0, 2000),
    ),
    cb2=device(
        "nicos.devices.generic.ManualMove",
        description="vertical divergence after mono",
        default=800,
        unit="min",
        fmtstr="%6.1f",
        abslimits=(0, 2000),
    ),
    cb3=device(
        "nicos.devices.generic.ManualMove",
        description="vertical divergence before ana",
        default=800,
        unit="min",
        fmtstr="%6.1f",
        abslimits=(0, 2000),
    ),
    cb4=device(
        "nicos.devices.generic.ManualMove",
        description="vertical divergence after ana",
        default=800,
        unit="min",
        fmtstr="%6.1f",
        abslimits=(0, 2000),
    ),
    ca2=device(
        "nicos.devices.generic.ManualSwitch",
        description="post monochromator collimator",
        states=["none", "15m", "40m", "60m"],
    ),
    ca3=device(
        "nicos.devices.generic.ManualSwitch",
        description="pre analyser collimator",
        states=["none", "15m", "40m", "60m"],
    ),
    ca4=device(
        "nicos.devices.generic.ManualSwitch",
        description="post analyser collimator",
        states=["none", "15m", "40m", "60m"],
    ),
    befilter=device(
        "nicos.devices.generic.ManualSwitch",
        description="L-N2 cooled Be filter 17cm",
        states=["unused", "on ki", "on kf"],
    ),
    beofilter=device(
        "nicos.devices.generic.ManualSwitch",
        description="L-N2 cooled BeO filter 17cm",
        states=["unused", "on ki", "on kf"],
    ),
    pgfilter=device(
        "nicos.devices.generic.ManualSwitch",
        description="PG filter 6cm 3.5deg mosaic",
        states=["unused", "on ki", "on kf"],
    ),
    detector=device(
        "nicos.devices.generic.ManualSwitch",
        description="Detector used for measurement",
        states=["none", "det1", "det2"],
    ),
)
