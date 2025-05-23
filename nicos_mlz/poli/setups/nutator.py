description = "POLI nutator"

group = "lowlevel"

tango_base = "tango://phys.poli.frm2:10000/poli/"

devices = dict(
    co_nutator1=device(
        "nicos.devices.entangle.Sensor",
        visibility=(),
        tangodevice=tango_base + "nutator1/rotenc",
        unit="deg",
    ),
    mo_nutator1=device(
        "nicos.devices.entangle.Motor",
        visibility=(),
        tangodevice=tango_base + "nutator1/rotmot",
        abslimits=(-200, 200),
        unit="deg",
        precision=0.1,
    ),
    co_nutator2=device(
        "nicos.devices.entangle.Sensor",
        visibility=(),
        tangodevice=tango_base + "nutator2/rotenc",
        unit="deg",
    ),
    mo_nutator2=device(
        "nicos.devices.entangle.Motor",
        visibility=(),
        tangodevice=tango_base + "nutator2/rotmot",
        abslimits=(-200, 200),
        unit="deg",
        precision=0.1,
    ),
    nutator1=device(
        "nicos.devices.generic.Axis",
        description="nutator1 axis",
        motor="mo_nutator1",
        coder="co_nutator1",
        abslimits=(-200, 200),
        fmtstr="%.2f",
        precision=0.2,
        dragerror=45,
    ),
    nutator2=device(
        "nicos.devices.generic.Axis",
        description="nutator2 axis",
        motor="mo_nutator2",
        coder="co_nutator2",
        abslimits=(-200, 200),
        fmtstr="%.2f",
        precision=0.2,
        dragerror=45,
    ),
)
