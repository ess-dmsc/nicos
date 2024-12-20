description = "Pressure sensor of Pressure Box"

group = "optional"

tango_base = "tango://hw.sans1.frm2.tum.de:10000/sans1"

devices = dict(
    pressure_box=device(
        "nicos.devices.entangle.Sensor",
        description="pressure cell",
        tangodevice=tango_base + "/keller/sensor",
        fmtstr="%.2f",
        pollinterval=1,
        maxage=5,
        warnlimits=(0, 1),
    ),
)
