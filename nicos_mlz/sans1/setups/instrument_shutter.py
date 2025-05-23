description = "instrument shutter control"

tango_base = "tango://hw.sans1.frm2.tum.de:10000/sans1/instrument_shutter/"

devices = dict(
    # instrument_shutter = device('nicos.devices.generic.MultiSwitcher',
    instrument_shutter=device(
        "nicos_mlz.sans1.devices.shutter.Shutter",
        description="Instrument Shutter Switcher with readback",
        moveables=[
            device(
                "nicos.devices.entangle.DigitalOutput",
                tangodevice=tango_base + "pressure_valve",
                description="Instrument Shutter Valve",
                fmtstr="%d",
            ),
        ],
        readables=[
            device(
                "nicos.devices.entangle.DigitalInput",
                tangodevice=tango_base + "switch_open",
                description="Instrument Shutter Switch Open",
                fmtstr="%d",
            ),
            device(
                "nicos.devices.entangle.DigitalInput",
                tangodevice=tango_base + "switch_closed",
                description="Instrument Shutter Switch Closed",
                fmtstr="%d",
            ),
        ],
        mapping={
            "open": [1, 1, 0],
            "close": [0, 0, 1],
        },
        fallback="?",
        fmtstr="%s",
        precision=[0],
        blockingmove=False,
        # timeout = 5,
    ),
    #    valve = device('nicos.devices.entangle.DigitalOutput',
    #        tangodevice = tango_base + 'instrument_shutter/pressure_valve',
    #        description = 'Instrument Shutter Valve',
    #        visibility = (),
    #    ),
    #    switch_open = device('nicos.devices.entangle.DigitalInput',
    #        tangodevice = tango_base + 'instrument_shutter/switch_open',
    #        description = 'Instrument Shutter Switch Open',
    #        visibility = (),
    #    ),
    #    switch_closed = device('nicos.devices.entangle.DigitalInput',
    #        tangodevice = tango_base + 'instrument_shutter/switch_closed',
    #        description = 'Instrument Shutter Switch Closed',
    #        visibility = (),
    #    ),
)
