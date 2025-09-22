# ruff: noqa: F821
description = "The motors for alignment in the YMIR cave"


devices = dict(
    beamstop_1=device(
        "nicos.devices.generic.VirtualMotor",
        description="Single axis positioner",
        abslimits=(0.0, 17.0),
        unit="mm",
        speed=5,
    ),
    beamstop_2=device(
        "nicos.devices.generic.VirtualMotor",
        description="Single axis positioner",
        abslimits=(0.0, 17.0),
        unit="mm",
        speed=5,
    ),
    beamstop_3=device(
        "nicos.devices.generic.VirtualMotor",
        description="Single axis positioner",
        abslimits=(0.0, 17.0),
        unit="mm",
        speed=5,
    ),
    beamstop_4=device(
        "nicos.devices.generic.VirtualMotor",
        description="Single axis positioner",
        abslimits=(0.0, 17.0),
        unit="mm",
        speed=5,
    ),
    beamstop_seq=device(
        "nicos_ess.devices.sequencers.BeamStopSequencer",
        description="Sequencer for the four beamstops",
        inpos=15.0,
        outpos=0.0,
        mapping={
            "beamstop 1": "bs1",
            "beamstop 2": "bs2",
            "beamstop 3": "bs3",
            "beamstop 4": "bs4",
            "out": "out",
        },
        bs1="beamstop_1",
        bs2="beamstop_2",
        bs3="beamstop_3",
        bs4="beamstop_4",
    ),
)
