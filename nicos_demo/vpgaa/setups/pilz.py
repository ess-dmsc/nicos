description = "Shutter and attenuators via Pilz box"

group = "lowlevel"

devices = dict(
    shutter=device(
        "nicos.devices.generic.ManualSwitch",
        description="secondary experiment shutter",
        states=["open", "closed"],
    ),
    # attenuator = device('nicos_demo.demo.devices.attenuator.Attenuator',
    #     description = 'Attenuator',
    #     blades = ['att1', 'att2', 'att3'],
    # ),
    att1=device(
        "nicos.devices.generic.ManualSwitch",
        description="attenuator 1",
        states=["in", "out"],
    ),
    att2=device(
        "nicos.devices.generic.ManualSwitch",
        description="attenuator 2",
        states=["in", "out"],
    ),
    att3=device(
        "nicos.devices.generic.ManualSwitch",
        description="attenuator 3",
        states=["in", "out"],
    ),
    att=device(
        "nicos_mlz.pgaa.devices.Attenuator",
        description="Attenuator device",
        moveables=["att1", "att2", "att3"],
        readables=None,
        precision=None,
        unit="%",
        fmtstr="%.1f",
        mapping={
            100.0: ("out", "out", "out"),
            47.0: ("out", "in", "out"),
            16.0: ("in", "out", "out"),
            7.5: ("in", "in", "out"),
            5.9: ("out", "out", "in"),
            3.5: ("out", "in", "in"),
            2.7: ("in", "out", "in"),
            1.6: ("in", "in", "in"),
        },
    ),
)
