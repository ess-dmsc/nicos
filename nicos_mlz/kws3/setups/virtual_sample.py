description = "Virtual Sample setup"
group = "lowlevel"
display_order = 35

includes = ["virtual_mirror", "virtual_resolution"]

pos_presets = configdata("config_sample_pos.SAMPLE_POS_PRESETS")

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
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample 1st x-table",
        visibility=(),
    ),
    sam_hub_y=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample 1st y-table",
        visibility=(),
    ),
    sam10_x=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample 1st x-table in vacuum chamber",
        visibility=(),
    ),
    sam10_y=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample 1st y-table in vacuum chamber",
        visibility=(),
    ),
    sam10_ap_x_left=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture in 1st sample chamber left",
        visibility=(),
    ),
    sam10_ap_x_right=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture in 1st sample chamber right",
        visibility=(),
    ),
    sam10_ap_y_upper=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture in 1st sample chamber upper",
        visibility=(),
    ),
    sam10_ap_y_lower=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture in 1st sample chamber lower",
        visibility=(),
    ),
    sam10_ap=device(
        "nicos.devices.generic.Slit",
        description="aperture inside 1st sample chamber",
        coordinates="opposite",
        opmode="offcentered",
        left="sam10_ap_x_left",
        right="sam10_ap_x_right",
        bottom="sam10_ap_y_lower",
        top="sam10_ap_y_upper",
        visibility=(),
    ),
    sam01_x=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample 2nd x-table in vacuum chamber",
        visibility=(),
    ),
    sam01_y=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample 2nd y-table in vacuum chamber",
        visibility=(),
    ),
    sam01_ap_x_left=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture sample 2nd jj-xray left",
        visibility=(),
    ),
    sam01_ap_x_right=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture sample 2nd jj-xray right",
        visibility=(),
    ),
    sam01_ap_y_upper=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture sample 2st jj-xray upper",
        visibility=(),
    ),
    sam01_ap_y_lower=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="aperture sample 2st jj-xray lower",
        visibility=(),
    ),
    sam01_ap=device(
        "nicos.devices.generic.Slit",
        description="sample 2nd aperture jj-xray",
        coordinates="opposite",
        opmode="offcentered",
        left="sam01_ap_x_left",
        right="sam01_ap_x_right",
        bottom="sam01_ap_y_lower",
        top="sam01_ap_y_upper",
        visibility=(),
    ),
)

alias_config = {
    "sam_ap": {"sam10_ap": 100, "sam01_ap": 90},
    "sam_x": {"sam10_x": 100, "sam01_x": 90},
    "sam_y": {"sam10_y": 100, "sam01_y": 90},
}
