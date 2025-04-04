description = "vacuum system monitoring"

group = "lowlevel"

tango_base = "tango://phys.kws3.frm2:10000/kws3/"
s7_analog = tango_base + "s7_io/"

devices = dict(
    pi2_1=device(
        "nicos.devices.entangle.Sensor",
        description="pressure in selector",
        tangodevice=s7_analog + "pi2_1",
        unit="mbar",
        fmtstr="%.1e",
        visibility=(),
    ),
    pi2_2=device(
        "nicos.devices.entangle.Sensor",
        description="pressure in tube 1",
        tangodevice=s7_analog + "pi2_2",
        unit="mbar",
        fmtstr="%.1e",
        visibility=(),
    ),
    pi3_1=device(
        "nicos.devices.entangle.Sensor",
        description="pressure in mirror chamber",
        tangodevice=s7_analog + "pi3_1",
        unit="mbar",
        fmtstr="%.1e",
        visibility=(),
    ),
    pi1_1=device(
        "nicos.devices.entangle.Sensor",
        description="pressure in sample chamber 1",
        tangodevice=s7_analog + "pi1_1",
        unit="mbar",
        fmtstr="%.1e",
        visibility=(),
    ),
    pi2_4=device(
        "nicos.devices.entangle.Sensor",
        description="pressure in tube 2",
        tangodevice=s7_analog + "pi2_4",
        unit="mbar",
        fmtstr="%.1e",
        visibility=(),
    ),
    pi1_2=device(
        "nicos.devices.entangle.Sensor",
        description="pressure in sample chamber 2",
        tangodevice=s7_analog + "pi1_2",
        unit="mbar",
        fmtstr="%.1e",
        visibility=(),
    ),
    pi1_3=device(
        "nicos.devices.entangle.Sensor",
        description="pressure in tube 3",
        tangodevice=s7_analog + "pi1_3",
        unit="mbar",
        fmtstr="%.1e",
        visibility=(),
    ),
)
