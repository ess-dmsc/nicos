description = "Analyzer devices"

group = "lowlevel"

includes = ["aliases"]

devices = dict(
    ath=device(
        "nicos.devices.generic.Axis",
        description="Rocking angle theta of analyser",
        motor=device(
            "nicos.devices.generic.VirtualMotor",
            unit="deg",
            abslimits=(-0, 60),
            speed=0.5,
        ),
        precision=0.01,
        # offset = -0.551,
        maxtries=8,
    ),
    st_att=device(
        "nicos.devices.generic.VirtualMotor",
        unit="deg",
        abslimits=(-117, 117),
        speed=0.5,
        visibility=(),
    ),
    att=device(
        "nicos.devices.generic.Axis",
        description="Scattering angle two-theta of analyser",
        motor="st_att",
        precision=0.01,
        # offset = 0.205,
        jitter=0.2,
        dragerror=1,
        maxtries=30,
    ),
    afpg=device(
        "nicos_mlz.puma.devices.FocusAxis",
        description="Horizontal focus of PG-analyser",
        motor=device(
            "nicos_mlz.puma.devices.VirtualReferenceMotor",
            abslimits=(-8, 70),
            speed=1,
            unit="deg",
        ),
        uplimit=70,
        lowlimit=-8,
        abslimits=(-8, 70),
        flatpos=4.92,
        startpos=4,
        precision=0.05,
        maxtries=15,
    ),
    afge=device(
        "nicos_mlz.puma.devices.FocusAxis",
        description="Horizontal focus of Ge-analyser",
        motor=device(
            "nicos_mlz.puma.devices.VirtualReferenceMotor",
            unit="deg",
            abslimits=(-55, 55),
            speed=1,
        ),
        uplimit=55,
        lowlimit=-55,
        abslimits=(-55, 55),
        flatpos=4.92,
        startpos=4,
        precision=0.25,
        maxtries=15,
    ),
)
