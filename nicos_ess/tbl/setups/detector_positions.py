description = "Measured detector positions along z, with the sample at z = 0"

group = "optional"

devices = dict(
    measured_he3_bank_0_z=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured z position of He-3 tube bank 0",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
    measured_he3_bank_1_z=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured z position of He-3 tube bank 1",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
    measured_ngem_z=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured z position of the nGEM detector",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
    measured_multiblade_z=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured z position of the Multi-Blade detector",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
    measured_timepix3_z=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured z position of the Timepix3 detector",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
    measured_orca_z=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Measured z position of the ORCA camera",
        default=0,
        unit="m",
        abslimits=(-10, 10),
    ),
)
