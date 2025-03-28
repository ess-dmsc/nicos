description = "Double Crystal Monochromator"

group = "optional"

tango_base = "tango://antareshw.antares.frm2.tum.de:10000/antares/"

devices = dict(
    mono=device(
        "nicos_mlz.antares.devices.Monochromator",
        description="ANTARES PG Double Crystal Monochromator",
        dvalue1=3.354,
        dvalue2=3.354,
        distance=97,
        phi1="mr1",
        phi2="mr2",
        translation="mtz",
        inout="mono_inout",
        abslimits=(1.4, 6.5),
        userlimits=(1.4, 6.5),
        maxage=5,
        pollinterval=3,
        parkingpos={"phi1": 12, "phi2": 12, "translation": -50, "inout": "out"},
    ),
    mr1=device(
        "nicos.devices.entangle.Motor",
        description="Rotation of first monochromator crystal",
        tangodevice=tango_base + "fzjs7/mr1",
        # tangodevice = tango_base + 'copley/m11',
        speed=5,
        unit="deg",
        abslimits=(12, 66),
        maxage=5,
        pollinterval=3,
        visibility=(),
        precision=0.01,
    ),
    mr2=device(
        "nicos.devices.entangle.Motor",
        description="Rotation of second monochromator crystal",
        tangodevice=tango_base + "fzjs7/mr2",
        # tangodevice = tango_base + 'copley/m12',
        speed=5,
        unit="deg",
        abslimits=(12, 66),
        maxage=5,
        pollinterval=3,
        visibility=(),
        precision=0.01,
    ),
    mtz=device(
        "nicos.devices.entangle.Motor",
        description="Translation of second monochromator crystal",
        tangodevice=tango_base + "fzjs7/mtz",
        # tangodevice = tango_base + 'copley/m13',
        speed=5,
        unit="mm",
        abslimits=(-120, 260),
        userlimits=(-120, 260),
        maxage=5,
        pollinterval=3,
        visibility=(),
        precision=0.01,
    ),
    mono_io=device(
        "nicos.devices.entangle.DigitalOutput",
        description="Moves Monochromator in and out of beam",
        tangodevice=tango_base + "fzjdp_digital/Monochromator",
        unit="",
        maxage=5,
        pollinterval=3,
        visibility=(),
    ),
    mono_inout=device(
        "nicos.devices.generic.Switcher",
        description="Moves Monochromator in and out of beam",
        moveable="mono_io",
        mapping={"in": 1, "out": 2},
        fallback="<undefined>",
        unit="",
        maxage=5,
        pollinterval=3,
        precision=0,
        visibility=(),
    ),
    monoswitch_io=device(
        "nicos.devices.entangle.DigitalOutput",
        description="Tango device for Monoswitch in/out",
        tangodevice=tango_base + "fzjdp_digital/Monochromator",
        visibility=(),
    ),
    monoswitch=device(
        "nicos.devices.generic.Switcher",
        description="Monochromator switch in/out",
        moveable="monoswitch_io",
        mapping={"in": 1, "out": 2},
        fallback="<undefined>",
        precision=0,
    ),
)

monitor_blocks = dict(
    default=Block(
        "Double Crystal PG Monochromator",
        [
            BlockRow(
                Field(name="Lambda", dev="mono"),
                Field(name="Position", dev="mono_inout"),
            ),
            BlockRow(
                Field(dev="mr1"),
                Field(dev="mr2"),
                Field(dev="mtz"),
            ),
        ],
        setups=setupname,
    ),
)
