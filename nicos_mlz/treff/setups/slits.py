description = "Slits"

group = "lowlevel"

tango_base = "tango://phys.treff.frm2:10000/treff/FZJS7/"

devices = dict(
    s1_left=device(
        "nicos.devices.entangle.Motor",
        description="Left blade of slit 1",
        tangodevice=tango_base + "s1_left",
        unit="mm",
        precision=0.01,
        fmtstr="%.2f",
    ),
    s1_right=device(
        "nicos.devices.entangle.Motor",
        description="Right blade of slit 1",
        tangodevice=tango_base + "s1_right",
        unit="mm",
        precision=0.01,
        fmtstr="%.2f",
    ),
    s1_bottom=device(
        "nicos.devices.entangle.Motor",
        description="Bottom blade of slit 1",
        tangodevice=tango_base + "s1_bottom",
        unit="mm",
        precision=0.01,
        fmtstr="%.2f",
    ),
    s1_top=device(
        "nicos.devices.entangle.Motor",
        description="Left blade of slit 1",
        tangodevice=tango_base + "s1_top",
        unit="mm",
        precision=0.01,
        fmtstr="%.2f",
    ),
    s1=device(
        "nicos.devices.generic.Slit",
        description="Slit 1",
        left="s1_left",
        right="s1_right",
        bottom="s1_bottom",
        top="s1_top",
        opmode="centered",
        coordinates="opposite",
    ),
    s2_left=device(
        "nicos.devices.entangle.Motor",
        description="Left blade of slit 2",
        tangodevice=tango_base + "s2_left",
        unit="mm",
        precision=0.01,
        fmtstr="%.2f",
    ),
    s2_right=device(
        "nicos.devices.entangle.Motor",
        description="Right blade of slit 2",
        tangodevice=tango_base + "s2_right",
        unit="mm",
        precision=0.01,
        fmtstr="%.2f",
    ),
    s2_bottom=device(
        "nicos.devices.entangle.Motor",
        description="Bottom blade of slit 2",
        tangodevice=tango_base + "s2_bottom",
        unit="mm",
        precision=0.01,
        fmtstr="%.2f",
    ),
    s2_top=device(
        "nicos.devices.entangle.Motor",
        description="Top blade of slit 2",
        tangodevice=tango_base + "s2_top",
        unit="mm",
        precision=0.01,
        fmtstr="%.2f",
    ),
    s2=device(
        "nicos.devices.generic.Slit",
        description="Slit 2",
        left="s2_left",
        right="s2_right",
        bottom="s2_bottom",
        top="s2_top",
        opmode="centered",
        coordinates="opposite",
    ),
)
