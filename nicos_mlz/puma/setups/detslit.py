description = "Slits before detector"

group = "optional"

includes = ["motorbus6"]

devices = dict(
    st_dslit=device(
        "nicos_mlz.puma.devices.Motor",
        bus="motorbus6",
        addr=67,
        slope=4500,
        unit="mm",
        abslimits=(-5.5, 30),
        zerosteps=500000,
        visibility=(),
    ),
    co_dslit=device(
        "nicos_mlz.puma.devices.Coder",
        bus="motorbus6",
        addr=97,
        poly=[-159.0 / 80, 1.0 / 80],
        unit="mm",
        visibility=(),
    ),
    dslit=device(
        "nicos.devices.generic.Axis",
        description="Slit before detector",
        motor="st_dslit",
        coder="co_dslit",
        precision=0.05,
        offset=0,
        maxtries=10,
    ),
)
