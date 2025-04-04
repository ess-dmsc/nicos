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
    ),
    qepro=device(
        "nicos_ess.devices.virtual.spectrometer.VirtualSpectrometer",
        description="A dummy spectrometer",
        pva=True,
        pollinterval=0.5,
        maxage=None,
        monitor=True,
        acquireunits="ms",
    ),
)
