description = "HR spectrometer for testing in LoKI"

devices = dict(
    hr4=device(
        "nicos_ess.devices.virtual.spectrometer.VirtualSpectrometer",
        description="A dummy spectrometer",
        pva=True,
        pollinterval=0.5,
        maxage=None,
        monitor=True,
        acquireunits="us",
        virtualgauss=["hr4_vg"],
    ),
    hr4_vg=device("nicos.devices.generic.virtual.VirtualGauss", motors=["hr4_motor"]),
    hr4_motor=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Spectrometer virtual motor",
        abslimits=(-200, 200),
        unit="mm",
    ),
    qepro=device(
        "nicos_ess.devices.virtual.spectrometer.VirtualSpectrometer",
        description="A dummy spectrometer",
        pva=True,
        pollinterval=0.5,
        maxage=None,
        monitor=True,
        acquireunits="ms",
        virtualgauss=["qepro_vg"],
    ),
    qepro_vg=device(
        "nicos.devices.generic.virtual.VirtualGauss", motors=["qepro_motor"]
    ),
    qepro_motor=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Spectrometer virtual motor",
        abslimits=(-200, 200),
        unit="mm",
    ),
)
