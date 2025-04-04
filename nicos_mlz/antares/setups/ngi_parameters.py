description = "Non-electronically adjustable parameters of the nGI"

group = "optional"

devices = dict(
    G0_grating=device(
        "nicos.devices.generic.manual.ManualSwitch",
        description="Grating installed at G0 position",
        states=[
            "P0_150um DC0_0.18 h0_180um",
            "P0_150um DC0_0.28 h0_180um",
            "P0_150um DC0_0.38 h0_180um",
            "P0_150um DC0_0.48 h0_180um",
            "other",
        ],
    ),
    G1_grating=device(
        "nicos.devices.generic.manual.ManualSwitch",
        description="Grating installed at G1 position",
        states=[
            "P1_24.4um DC1_0.49 h1_41um",
            "P1_24.4um DC1_0.55 h1_123um",
            "other",
        ],
    ),
    G2_grating=device(
        "nicos.devices.generic.manual.ManualSwitch",
        description="Grating installed at G2 position",
        states=[
            "P2_13.3um DC2_0.45 h2_85um",
            "other",
        ],
    ),
    G0_position=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Position along z-axis of G0",
        unit="mm",
        abslimits=(0, 20000),
    ),
    G1_position=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Position along z-axis of G1",
        unit="mm",
        abslimits=(0, 20000),
    ),
    G2_position=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Position along z-axis of G2",
        unit="mm",
        abslimits=(0, 20000),
    ),
    sample_position=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Position along z-axis of the sample",
        unit="mm",
        abslimits=(0, 20000),
    ),
    detector_position=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Position along z-axis of the detector",
        unit="mm",
        abslimits=(0, 20000),
    ),
)
