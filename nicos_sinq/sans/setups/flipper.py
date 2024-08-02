description = "Devices for the HAMEG 8131 spin flipper"

pvprefix = "SQ:SANS:flip"

devices = dict(
    flip_freq=device(
        "nicos_sinq.devices.epics.generic.WindowMoveable",
        description="Set frequency",
        readpv=pvprefix + ":FREQ_RBV",
        writepv=pvprefix + ":FREQ",
        abslimits=(100e-6, 15e06),
        precision=5.0,
    ),
    flip_amp=device(
        "nicos_sinq.devices.epics.generic.WindowMoveable",
        description="Set amplitude",
        readpv=pvprefix + ":AMP_RBV",
        writepv=pvprefix + ":AMP",
        abslimits=(20e-3, 20.0),
        precision=0.2,
    ),
    flip_off=device(
        "nicos_sinq.devices.epics.generic.WindowMoveable",
        description="Set offset",
        readpv=pvprefix + ":OFF_RBV",
        writepv=pvprefix + ":OFF",
        abslimits=(-5, 5),
        precision=0.2,
    ),
    flip_port=device(
        "nicos_sinq.devices.epics.extensions.EpicsCommandReply",
        description="Direct connection to spin flipper",
        commandpv=pvprefix + ".AOUT",
        replypv=pvprefix + ".AINP",
    ),
    flip=device(
        "nicos_sinq.sans.devices.hameg8131.HAMEG8131",
        description="Flipper control",
        readpv=pvprefix + ":STATE_RBV",
        writepv=pvprefix + ":STATE",
        port="flip_port",
        amp="flip_amp",
        freq="flip_freq",
    ),
)
