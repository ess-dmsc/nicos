description = "Collimation setup"
group = "lowlevel"
display_order = 10

includes = ["vacuumsys"]
excludes = ["virtual_collimation"]

presets = configdata("config_collimation.COLLIMATION_PRESETS")

tango_base = "tango://phys.kws2.frm2:10000/kws2/"

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
    coll_set=device(
        "nicos.devices.entangle.DigitalOutput",
        tangodevice=tango_base + "sps/coll_write",
        fmtstr="%#x",
        visibility=(),
    ),
    coll_in=device(
        "nicos.devices.entangle.DigitalInput",
        tangodevice=tango_base + "sps/coll_in",
        fmtstr="%#x",
        visibility=(),
    ),
    coll_out=device(
        "nicos.devices.entangle.DigitalInput",
        tangodevice=tango_base + "sps/coll_out",
        fmtstr="%#x",
        visibility=(),
    ),
    coll_sync=device(
        "nicos.devices.entangle.DigitalOutput",
        tangodevice=tango_base + "sps/sync_bit",
        fmtstr="%#x",
        visibility=(),
    ),
    coll_guides=device(
        "nicos_mlz.kws1.devices.collimation.CollimationGuides",
        description="positioning of the neutron guide elements",
        output="coll_set",
        input_in="coll_in",
        input_out="coll_out",
        sync_bit="coll_sync",
        first=4,
        fmtstr="%d",
        timeout=150.0,
    ),
    aperture_20=device(
        "nicos_mlz.kws1.devices.collimation.CollimationSlit",
        description="20m aperture",
        horizontal="aperture_20_x",
        vertical="aperture_20_y",
        openpos=(49.9, 49.9),
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
        openpos=(50.0, 50.0),
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
        "nicos_mlz.kws1.devices.collimation.SlitMotor",
        description="20m aperture horizontal opening",
        tangodevice=tango_base + "fzjs7/aperture_20_x",
        unit="mm",
        precision=0.1,
        visibility=(),
    ),
    aperture_20_y=device(
        "nicos_mlz.kws1.devices.collimation.SlitMotor",
        description="20m aperture vertical opening",
        tangodevice=tango_base + "fzjs7/aperture_20_y",
        unit="mm",
        precision=0.1,
        visibility=(),
    ),
    aperture_14_x=device(
        "nicos_mlz.kws1.devices.virtual.NonvirtualStandin",
        description="14m aperture horizontal opening",
        visibility=(),
    ),
    aperture_14_y=device(
        "nicos_mlz.kws1.devices.virtual.NonvirtualStandin",
        description="14m aperture vertical opening",
        visibility=(),
    ),
    #    aperture_14_x = device('nicos_mlz.kws1.devices.collimation.SlitMotor',
    #                           description = '14m aperture horizontal opening',
    #                           tangodevice = tango_base + 'fzjs7/aperture_14_x',
    #                           unit = 'mm',
    #                           precision = 0.1,
    #                           visibility = (),
    #                           abslimits = (1, 50.0),
    #                          ),
    #    aperture_14_y = device('nicos_mlz.kws1.devices.collimation.SlitMotor',
    #                           description = '14m aperture vertical opening',
    #                           tangodevice = tango_base + 'fzjs7/aperture_14_y',
    #                           unit = 'mm',
    #                           precision = 0.1,
    #                           visibility = (),
    #                          ),
    #
    aperture_08_x=device(
        "nicos_mlz.kws1.devices.collimation.SlitMotor",
        description="8m aperture horizontal opening",
        tangodevice=tango_base + "fzjs7/aperture_8_x",
        unit="mm",
        precision=0.1,
        visibility=(),
    ),
    aperture_08_y=device(
        "nicos_mlz.kws1.devices.collimation.SlitMotor",
        description="8m aperture vertical opening",
        tangodevice=tango_base + "fzjs7/aperture_8_y",
        unit="mm",
        precision=0.1,
        visibility=(),
    ),
    aperture_04_x=device(
        "nicos_mlz.kws1.devices.collimation.SlitMotor",
        description="4m aperture horizontal opening",
        tangodevice=tango_base + "fzjs7/aperture_4_x",
        unit="mm",
        precision=0.1,
        visibility=(),
        abslimits=(1, 50.0),
    ),
    aperture_04_y=device(
        "nicos_mlz.kws1.devices.collimation.SlitMotor",
        description="4m aperture vertical opening",
        tangodevice=tango_base + "fzjs7/aperture_4_y",
        unit="mm",
        precision=0.1,
        visibility=(),
        abslimits=(1, 50.0),
    ),
    aperture_02_x=device(
        "nicos_mlz.kws1.devices.collimation.SlitMotor",
        description="2m aperture horizontal opening",
        tangodevice=tango_base + "fzjs7/aperture_2_x",
        unit="mm",
        precision=0.1,
        visibility=(),
    ),
    aperture_02_y=device(
        "nicos_mlz.kws1.devices.collimation.SlitMotor",
        description="2m aperture vertical opening",
        tangodevice=tango_base + "fzjs7/aperture_2_y",
        unit="mm",
        precision=0.1,
        visibility=(),
    ),
    # only used manually
    aperture_20_h=device(
        "nicos.devices.entangle.Motor",
        description="20m aperture vertical positioning",
        tangodevice=tango_base + "fzjs7/aperture_20_h",
        unit="mm",
        precision=0.1,
        visibility=(),
    ),
)

extended = dict(
    representative="collimation",
)
