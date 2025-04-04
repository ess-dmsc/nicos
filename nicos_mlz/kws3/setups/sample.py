description = "General sample aliases"
group = "lowlevel"
display_order = 35

includes = ["mirror", "resolution"]
excludes = ["virtual_sample"]

pos_presets = configdata("config_sample_pos.SAMPLE_POS_PRESETS")

tango_base = "tango://phys.kws3.frm2:10000/kws3/"
s7_motor = tango_base + "s7_motor/"

devices = dict(
    sam_x=device(
        "nicos.devices.generic.DeviceAlias",
        description="currently active sample x table",
    ),
    sam_y=device(
        "nicos.devices.generic.DeviceAlias",
        description="currently active sample y table",
    ),
    sam_ap=device(
        "nicos.devices.generic.DeviceAlias",
        description="currently active sample aperture",
    ),
    sample_pos=device(
        "nicos_mlz.kws3.devices.sample.SamplePos",
        description="switcher for sample position presets",
        active_x="sam_x",
        active_y="sam_y",
        active_ap="sam_ap",
        alloweddevs=[
            "mir_ap2",
            "sam10_ap",
            "sam01_ap",
            "sam10_x",
            "sam10_y",
            "sam01_x",
            "sam01_y",
        ],
        presets=pos_presets,
    ),
    sam_hub_x=device(
        "nicos.devices.entangle.Motor",
        description="sample 1st x-table",
        tangodevice=s7_motor + "sam_hub_x",
        visibility=(),
        unit="mm",
        precision=0.01,
    ),
    sam_hub_y=device(
        "nicos.devices.entangle.Motor",
        description="sample 1st y-table",
        tangodevice=s7_motor + "sam_hub_y",
        visibility=(),
        unit="mm",
        precision=0.01,
    ),
    sam_hub_mobil_y=device(
        "nicos.devices.entangle.Motor",
        description="sample mobile y-table",
        tangodevice=s7_motor + "sam_hub_mobil_y",
        visibility=(),
        unit="mm",
        precision=0.01,
    ),
    sam10_x=device(
        "nicos.devices.entangle.Motor",
        description="sample 1st x-table in vacuum chamber",
        tangodevice=s7_motor + "sam10_x",
        visibility=(),
        unit="mm",
        precision=0.01,
    ),
    sam10_y=device(
        "nicos.devices.entangle.Motor",
        description="sample 1st y-table in vacuum chamber",
        tangodevice=s7_motor + "sam10_y",
        visibility=(),
        unit="mm",
        precision=0.01,
    ),
    sam10_ap_x_left=device(
        "nicos.devices.entangle.Motor",
        description="aperture 1st sample chamber left",
        tangodevice=s7_motor + "sam10_ap_x_left",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    sam10_ap_x_right=device(
        "nicos.devices.entangle.Motor",
        description="aperture 1st sample chamber right",
        tangodevice=s7_motor + "sam10_ap_x_right",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    sam10_ap_y_upper=device(
        "nicos.devices.entangle.Motor",
        description="aperture 1st sample chamber upper",
        tangodevice=s7_motor + "sam10_ap_y_upper",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    sam10_ap_y_lower=device(
        "nicos.devices.entangle.Motor",
        description="aperture 1st sample chamber lower",
        tangodevice=s7_motor + "sam10_ap_y_lower",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    sam10_ap=device(
        "nicos.devices.generic.Slit",
        description="aperture inside 1st sample chamber",
        coordinates="opposite",
        visibility=(),
        opmode="offcentered",
        fmtstr="(%.2f, %.2f) %.2f x %.2f",
        left="sam10_ap_x_left",
        right="sam10_ap_x_right",
        bottom="sam10_ap_y_lower",
        top="sam10_ap_y_upper",
        parallel_ref=True,
    ),
    sam01_x=device(
        "nicos.devices.entangle.Motor",
        description="sample 2nd x-table in vacuum chamber",
        tangodevice=s7_motor + "sam01_x",
        visibility=(),
        unit="mm",
        precision=0.01,
        fmtstr="%.2f",
    ),
    sam01_y=device(
        "nicos.devices.entangle.Motor",
        description="sample 2nd y-table in vacuum chamber",
        tangodevice=s7_motor + "sam01_y",
        visibility=(),
        unit="mm",
        precision=0.01,
        fmtstr="%.2f",
    ),
    sam01_ap_x_left=device(
        "nicos.devices.entangle.Motor",
        description="aperture sample 2nd jj-xray left",
        tangodevice=s7_motor + "sam01_ap_x_left",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    sam01_ap_x_right=device(
        "nicos.devices.entangle.Motor",
        description="aperture sample 2nd jj-xray right",
        tangodevice=s7_motor + "sam01_ap_x_right",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    sam01_ap_y_upper=device(
        "nicos.devices.entangle.Motor",
        description="aperture sample 2nd jj-xray upper",
        tangodevice=s7_motor + "sam01_ap_y_upper",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    sam01_ap_y_lower=device(
        "nicos.devices.entangle.Motor",
        description="aperture sample 2nd jj-xray lower",
        tangodevice=s7_motor + "sam01_ap_y_lower",
        unit="mm",
        precision=0.01,
        visibility=(),
    ),
    sam01_ap=device(
        "nicos.devices.generic.Slit",
        description="sample 2nd aperture jj-xray",
        coordinates="opposite",
        visibility=(),
        opmode="offcentered",
        fmtstr="(%.2f, %.2f) %.2f x %.2f",
        left="sam01_ap_x_left",
        right="sam01_ap_x_right",
        bottom="sam01_ap_y_lower",
        top="sam01_ap_y_upper",
        parallel_ref=True,
    ),
)

extended = dict(
    representative="sample_pos",
)

alias_config = {
    "sam_ap": {"sam10_ap": 100, "sam01_ap": 90},
    "sam_x": {"sam10_x": 100, "sam01_x": 90},
    "sam_y": {"sam10_y": 100, "sam01_y": 90},
}
