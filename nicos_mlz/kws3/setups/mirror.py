description = "Mirror area setup"
group = "lowlevel"
display_order = 30

includes = ["sample"]
excludes = ["virtual_mirror"]

tango_base = "tango://phys.kws3.frm2:10000/kws3/"
s7_motor = tango_base + "s7_motor/"

devices = dict(
    mir_x=device(
        "nicos.devices.entangle.Motor",
        description="mirror x-table",
        tangodevice=s7_motor + "mir_x",
        unit="mm",
        precision=0.01,
        fmtstr="%.3f",
        visibility=(),
    ),
    mir_y=device(
        "nicos.devices.entangle.Motor",
        description="mirror y-hub",
        tangodevice=s7_motor + "mir_y",
        unit="mm",
        precision=0.01,
        fmtstr="%.3f",
        visibility=(),
    ),
    mir_tilt=device(
        "nicos.devices.entangle.Motor",
        description="mirror tilting",
        tangodevice=s7_motor + "mir_tilt",
        unit="mm",
        precision=0.01,
        fmtstr="%.3f",
        visibility=(),
    ),
    mir_pos=device(
        "nicos_mlz.kws3.devices.combined.Mirror",
        description="overall mirror position",
        x="mir_x",
        y="mir_y",
        tilt="mir_tilt",
    ),
    mir_ap1=device(
        "nicos.devices.generic.Slit",
        description="jj-xray aperture in front of mirror",
        coordinates="opposite",
        opmode="offcentered",
        fmtstr="(%.2f, %.2f) %.2f x %.2f",
        left="mir_ap1_x_left",
        right="mir_ap1_x_right",
        bottom="mir_ap1_y_lower",
        top="mir_ap1_y_upper",
        parallel_ref=True,
        visibility=(),
    ),
    mir_ap1_x_left=device(
        "nicos.devices.entangle.Motor",
        description="aperture in front of mirror left",
        tangodevice=s7_motor + "mir_ap1_x_left",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    mir_ap1_x_right=device(
        "nicos.devices.entangle.Motor",
        description="aperture in front of mirror right",
        tangodevice=s7_motor + "mir_ap1_x_right",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    mir_ap1_y_upper=device(
        "nicos.devices.entangle.Motor",
        description="aperture in front of mirror upper",
        tangodevice=s7_motor + "mir_ap1_y_upper",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    mir_ap1_y_lower=device(
        "nicos.devices.entangle.Motor",
        description="aperture in front of mirror lower",
        tangodevice=s7_motor + "mir_ap1_y_lower",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    mir_ap2=device(
        "nicos.devices.generic.Slit",
        description="jj-xray aperture behind mirror",
        coordinates="opposite",
        opmode="offcentered",
        fmtstr="(%.2f, %.2f) %.2f x %.2f",
        left="mir_ap2_x_left",
        right="mir_ap2_x_right",
        bottom="mir_ap2_y_lower",
        top="mir_ap2_y_upper",
        parallel_ref=True,
        visibility=(),
    ),
    mir_ap2_x_left=device(
        "nicos.devices.entangle.Motor",
        description="aperture behind mirror left",
        tangodevice=s7_motor + "mir_ap2_x_left",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    mir_ap2_x_right=device(
        "nicos.devices.entangle.Motor",
        description="aperture behind mirror right",
        tangodevice=s7_motor + "mir_ap2_x_right",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    mir_ap2_y_upper=device(
        "nicos.devices.entangle.Motor",
        description="aperture behind mirror upper",
        tangodevice=s7_motor + "mir_ap2_y_upper",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    mir_ap2_y_lower=device(
        "nicos.devices.entangle.Motor",
        description="aperture behind mirror lower",
        tangodevice=s7_motor + "mir_ap2_y_lower",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
)

alias_config = {
    "sam_ap": {"mir_ap2": 80},
}

extended = dict(
    representative="mir_pos",
)
