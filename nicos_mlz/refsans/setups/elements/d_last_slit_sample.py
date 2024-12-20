description = "Sample positions"

group = "lowlevel"

devices = dict(
    d_last_slit_sample=device("nicos.devices.generic.DeviceAlias"),
    sample_x_manual=device(
        "nicos.devices.generic.ManualMove",
        description="distance last slit to samplecenter max105mm at pivot 9",
        abslimits=(0, 1000),
        default=100,
        fmtstr="%.1f",
        unit="mm",
    ),
)

alias_config = {
    "d_last_slit_sample": {"sample_x_manual": 100},
}
