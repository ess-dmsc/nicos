description = "correction coil motors"

group = "optional"

tango_base = "tango://phys.j-nse.frm2:10000/j-nse/"

devices = dict(
    cc_31b=device(
        "nicos.devices.entangle.Motor",
        description="correction coil A1 position",
        tangodevice=tango_base + "FZJS7/mo_cc31b",
        unit="mm",
        fmtstr="%.6f",
    ),
    cc_31a=device(
        "nicos.devices.entangle.Motor",
        description="correction coil A2 position",
        tangodevice=tango_base + "FZJS7/mo_cc31a",
        unit="mm",
        fmtstr="%.6f",
    ),
    cc_11b=device(
        "nicos.devices.entangle.Motor",
        description="correction coil A3 position",
        tangodevice=tango_base + "FZJS7/mo_cc11b",
        unit="mm",
        fmtstr="%.6f",
    ),
    cc_11a=device(
        "nicos.devices.entangle.Motor",
        description="correction coil A4 position",
        tangodevice=tango_base + "FZJS7/mo_cc11a",
        unit="mm",
        fmtstr="%.6f",
    ),
    cc_12b=device(
        "nicos.devices.entangle.Motor",
        description="correction coil B1 position",
        tangodevice=tango_base + "FZJS7/mo_cc12b",
        unit="mm",
        fmtstr="%.6f",
    ),
    cc_12a=device(
        "nicos.devices.entangle.Motor",
        description="correction coil B2 position",
        tangodevice=tango_base + "FZJS7/mo_cc12a",
        unit="mm",
        fmtstr="%.6f",
    ),
    cc_32a=device(
        "nicos.devices.entangle.Motor",
        description="correction coil B3 position",
        tangodevice=tango_base + "FZJS7/mo_cc32a",
        unit="mm",
        fmtstr="%.6f",
    ),
    cc_32b=device(
        "nicos.devices.entangle.Motor",
        description="correction coil B4 position",
        tangodevice=tango_base + "FZJS7/mo_cc32b",
        unit="mm",
        fmtstr="%.6f",
    ),
)
