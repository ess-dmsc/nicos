description = "LoKI manual distance measurements"

group = "optional"

devices = dict(
    measured_sample_position_z=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured position to the sample from the instrument zero, in axis Z",
        default=0,
        unit="m",
        abslimits=(-10, 0),
    ),
    measured_slit_set_4_z=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured position to slit set 4 from the instrument zero, in axis Z",
        default=0,
        unit="m",
        abslimits=(-10, 0),
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
