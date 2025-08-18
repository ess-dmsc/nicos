description = "LoKI manual distance measurements"

group = "optional"

devices = dict(
    measured_sample_position_z=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured position of the sample in axis Z",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
    measured_slit_set_4_z=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured position of slit set 4 in axis Z",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
    measured_slit_set_4_left_blade=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured position of slit set 4 left blade",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
    measured_slit_set_4_right_blade=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured position of slit set 4 right blade",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
    measured_slit_set_4_top_blade=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured position of slit set 4 top blade",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
    measured_slit_set_4_bottom_blade=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured position of slit set 4 bottom blade",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
)
