description = "Primary slit devices"

group = "lowlevel"

tango_base = "tango://motorbox01.stressi.frm2.tum.de:10000/box/"

devices = dict(
    slitm_w_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "channel5/motor",
        fmtstr="%.2f",
        visibility=(),
    ),
    slitm_w=device(
        "nicos.devices.generic.Axis",
        motor="slitm_w_m",
        fmtstr="%.2f",
        precision=0.1,
        visibility=(),
    ),
    slitm_h_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "channel6/motor",
        fmtstr="%.2f",
        visibility=(),
    ),
    slitm_h=device(
        "nicos.devices.generic.Axis",
        motor="slitm_h_m",
        fmtstr="%.2f",
        precision=0.1,
        visibility=(),
    ),
    slitm=device(
        "nicos.devices.generic.TwoAxisSlit",
        description="Monochromator entry slit",
        horizontal="slitm_w",
        vertical="slitm_h",
        pollinterval=60,
        maxage=90,
    ),
    slitm_e_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "channel7/motor",
        fmtstr="%.2f",
        visibility=(),
    ),
    slitm_e=device(
        "nicos.devices.generic.Axis",
        description="Monochromator exit slit width",
        motor="slitm_e_m",
        fmtstr="%.2f",
        precision=0.1,
    ),
    slits_d=device(
        "nicos.devices.entangle.Motor",
        description="Bottom blade of sample slit",
        tangodevice=tango_base + "channel2/motor",
        visibility=(),
    ),
    slits_u=device(
        "nicos.devices.entangle.Motor",
        description="Upper blade of the sample slit",
        tangodevice=tango_base + "channel1/motor",
        visibility=(),
    ),
    slits_l=device(
        "nicos.devices.entangle.Motor",
        description="Left blade of the sample slit",
        tangodevice=tango_base + "channel3/motor",
        visibility=(),
    ),
    slits_r=device(
        "nicos.devices.entangle.Motor",
        description="Right blade of the sample slit",
        tangodevice=tango_base + "channel4/motor",
        visibility=(),
    ),
    slits=device(
        "nicos.devices.generic.Slit",
        description="sample slit 4 blades",
        left="slits_l",
        right="slits_r",
        bottom="slits_d",
        top="slits_u",
        opmode="centered",
        coordinates="opposite",
        parallel_ref=True,
    ),
)
