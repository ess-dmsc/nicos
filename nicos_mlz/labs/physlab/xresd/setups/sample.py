description = "sample stage"
group = "optional"
display_order = 70

tango_base = configdata("instrument.values")["tango_base"] + "box/"

devices = dict(
    phis_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "huber/phi",
        unit="deg",
        precision=5e-3,
        fmtstr="%.3f",
        visibility=(),
    ),
    phis=device(
        "nicos.devices.generic.Axis",
        description="sample rotation around base normal",
        motor="phis_m",
        precision=5e-3,
    ),
    chis_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "huber/chi",
        unit="deg",
        precision=2.5e-4,
        fmtstr="%.4f",
        visibility=(),
    ),
    chis=device(
        "nicos.devices.generic.Axis",
        description="sample tilt around beam axis",
        motor="chis_m",
        precision=2.5e-4,
    ),
    omgs_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "bruker/theta",
        unit="deg",
        precision=1e-3,
        fmtstr="%.3f",
        visibility=(),
    ),
    omgs=device(
        "nicos.devices.generic.Axis",
        description="sample theta angle",
        motor="omgs_m",
        precision=1e-3,
    ),
    ctt=device(
        "nicos_mlz.labs.physlab.devices.coupled.CoupledMotor",
        description="Coupled Theta / 2Theta axis",
        maxis="tths",
        caxis="omgs",
        unit="deg",
        fmtstr="%.3f",
    ),
    tths_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "bruker/ttheta",
        unit="deg",
        precision=1e-3,
        fmtstr="%.3f",
        visibility=(),
    ),
    tths=device(
        "nicos.devices.generic.Axis",
        description="sample two-theta angle",
        motor="tths_m",
        precision=1e-3,
    ),
    stx_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "huber/x",
        unit="mm",
        precision=5e-4,
        fmtstr="%.4f",
        visibility=(),
    ),
    stx=device(
        "nicos.devices.generic.Axis",
        description="sample translation along the beam",
        motor="stx_m",
        precision=5e-4,
    ),
    sty_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "huber/y",
        unit="mm",
        precision=5e-4,
        fmtstr="%.4f",
        visibility=(),
    ),
    sty=device(
        "nicos.devices.generic.Axis",
        description="sample translation horizontally perpendicular to the beam",
        motor="sty_m",
        precision=5e-4,
    ),
    stz_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "huber/z",
        unit="mm",
        precision=1.5e-4,
        fmtstr="%.4f",
        visibility=(),
    ),
    stz=device(
        "nicos.devices.generic.Axis",
        description="sample translation in vertical direction",
        motor="stz_m",
        precision=1.5e-4,
    ),
)
