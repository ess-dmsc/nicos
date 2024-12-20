description = "Virtual mirror area setup"
group = "lowlevel"
display_order = 30

devices = dict(
    mir_x=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="mirror x-table",
    ),
    mir_y=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="mirror y-hub",
    ),
    mir_tilt=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="mirror area",
    ),
    mir_ap1=device(
        "nicos.devices.generic.Slit",
        description="jj-xray aperture in front of mirror",
        coordinates="opposite",
        opmode="offcentered",
        left="mir_ap1_x_left",
        right="mir_ap1_x_right",
        bottom="mir_ap1_y_lower",
        top="mir_ap1_y_upper",
    ),
    mir_ap1_x_left=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture in front of mirror left",
        visibility=(),
    ),
    mir_ap1_x_right=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture in front of mirror right",
        visibility=(),
    ),
    mir_ap1_y_upper=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture in front of mirror upper",
        visibility=(),
    ),
    mir_ap1_y_lower=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture in front of mirror lower",
        visibility=(),
    ),
    mir_ap2=device(
        "nicos.devices.generic.Slit",
        description="jj-xray aperture behind mirror",
        coordinates="opposite",
        opmode="offcentered",
        left="mir_ap2_x_left",
        right="mir_ap2_x_right",
        bottom="mir_ap2_y_lower",
        top="mir_ap2_y_upper",
    ),
    mir_ap2_x_left=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture behind mirror left",
        visibility=(),
    ),
    mir_ap2_x_right=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture behind mirror right",
        visibility=(),
    ),
    mir_ap2_y_upper=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture behind mirror upper",
        visibility=(),
    ),
    mir_ap2_y_lower=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture behind mirror lower",
        visibility=(),
    ),
)
