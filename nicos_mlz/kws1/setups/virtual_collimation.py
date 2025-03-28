description = "Virtual collimation setup"
group = "lowlevel"
display_order = 10

presets = configdata("config_collimation.COLLIMATION_PRESETS")

devices = dict(
    collimation=device(
        "nicos_mlz.kws1.devices.collimation.Collimation",
        description="high-level collimation device",
        mapping={k: (v["guides"], v["ap_x"], v["ap_y"]) for (k, v) in presets.items()},
        guides="coll_guides",
        slitpos=[2, 4, 8, 14, 20],
        slits=[
            "aperture_02",
            "aperture_04",
            "aperture_08",
            "aperture_14",
            "aperture_20",
        ],
    ),
    coll_guides=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="positioning of the neutron guide elements",
        fmtstr="%d",
    ),
    aperture_20=device(
        "nicos_mlz.kws1.devices.collimation.CollimationSlit",
        description="20m aperture",
        horizontal="aperture_20_x",
        vertical="aperture_20_y",
        openpos=(50.0, 50.0),
        fmtstr="%.1f x %.1f",
        visibility=(),
    ),
    aperture_14=device(
        "nicos_mlz.kws1.devices.collimation.CollimationSlit",
        description="14m aperture",
        horizontal="aperture_14_x",
        vertical="aperture_14_y",
        openpos=(50.0, 50.0),
        fmtstr="%.1f x %.1f",
        visibility=(),
    ),
    aperture_08=device(
        "nicos_mlz.kws1.devices.collimation.CollimationSlit",
        description="8m aperture",
        horizontal="aperture_08_x",
        vertical="aperture_08_y",
        openpos=(50.0, 50.0),
        fmtstr="%.1f x %.1f",
        visibility=(),
    ),
    aperture_04=device(
        "nicos_mlz.kws1.devices.collimation.CollimationSlit",
        description="4m aperture",
        horizontal="aperture_04_x",
        vertical="aperture_04_y",
        openpos=(49.9, 49.9),
        fmtstr="%.1f x %.1f",
        visibility=(),
    ),
    aperture_02=device(
        "nicos_mlz.kws1.devices.collimation.CollimationSlit",
        description="2m aperture",
        horizontal="aperture_02_x",
        vertical="aperture_02_y",
        openpos=(40.0, 40.0),
        fmtstr="%.1f x %.1f",
        visibility=(),
    ),
    aperture_20_x=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="20m aperture horizontal opening",
        visibility=(),
    ),
    aperture_20_y=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="20m aperture vertical opening",
        visibility=(),
    ),
    aperture_14_x=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="14m aperture horizontal opening",
        visibility=(),
    ),
    aperture_14_y=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="14m aperture vertical opening",
        visibility=(),
    ),
    aperture_08_x=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="8m aperture horizontal opening",
        visibility=(),
    ),
    aperture_08_y=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="8m aperture vertical opening",
        visibility=(),
    ),
    aperture_04_x=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="4m aperture horizontal opening",
        visibility=(),
    ),
    aperture_04_y=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="4m aperture vertical opening",
        visibility=(),
    ),
    aperture_02_x=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="2m aperture horizontal opening",
        visibility=(),
    ),
    aperture_02_y=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="2m aperture vertical opening",
        visibility=(),
    ),
)

extended = dict(
    representative="collimation",
)
