description = "Motor bus coder for mtt, mth"

group = "lowlevel"

tango_base = "tango://puma5.puma.frm2.tum.de:10000/puma/"

devices = dict(
    motorbus14=device(
        "nicos.devices.vendor.ipc.IPCModBusTango",
        tangodevice=tango_base + "motorbus14/bio",
        visibility=(),
    ),
)
