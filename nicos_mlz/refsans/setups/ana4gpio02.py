description = "Refsans 4 analog 1 GPIO on Raspberry"

group = "optional"

tango_base = "tango://%s:10000/test/ads/" % setupname
lowlevel = ()

devices = {
    "%s_ch1" % setupname: device(
        "nicos.devices.entangle.Sensor",
        description="ADin0",
        tangodevice=tango_base + "ch1",
        unit="V",
        fmtstr="%.4f",
        visibility=lowlevel,
    ),
    "%s_ch2" % setupname: device(
        "nicos.devices.entangle.Sensor",
        description="ADin1",
        tangodevice=tango_base + "ch2",
        unit="V",
        fmtstr="%.4f",
        visibility=lowlevel,
    ),
    "%s_ch3" % setupname: device(
        "nicos.devices.entangle.Sensor",
        description="ADin2",
        tangodevice=tango_base + "ch3",
        unit="V",
        fmtstr="%.4f",
        visibility=lowlevel,
    ),
    "%s_ch4" % setupname: device(
        "nicos.devices.entangle.Sensor",
        description="ADin3",
        tangodevice=tango_base + "ch4",
        unit="V",
        fmtstr="%.4f",
        visibility=lowlevel,
    ),
}
