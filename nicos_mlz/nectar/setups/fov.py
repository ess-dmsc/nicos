description = "FOV linear axis for the large box (300 x 300)"

group = "lowlevel"

includes = ["frr"]

tango_base = "tango://phytron01.nectar.frm2.tum.de:10000/"

devices = dict(
    fov_mot=device(
        "nicos.devices.entangle.Motor",
        description="FOV motor",
        tangodevice=tango_base + "box/FOV/mot",
        visibility=(),
    ),
    fov_enc=device(
        "nicos.devices.entangle.Sensor",
        description="FOV encoder",
        tangodevice=tango_base + "box/FOV/enc",
        visibility=(),
    ),
    fov=device(
        "nicos.devices.generic.Axis",
        description="FOV linear axis",
        pollinterval=5,
        maxage=10,
        precision=0.1,
        fmtstr="%.2f",
        motor="fov_mot",
        coder="fov_enc",
        backlash=-1,
    ),
)
