description = "Kompass setup for spherical polarisation analysis mode"

group = "optional"

tango_base = "tango://kompasshw.kompass.frm2.tum.de:10000/kompass/"

devices = dict(
    radial_coil1=device(
        "nicos.devices.entangle.PowerSupply",
        description="kepco power supply 1",
        tangodevice=tango_base + "kepco/current1",
        fmtstr="%.3f",
    ),
    axial_coil1=device(
        "nicos.devices.entangle.PowerSupply",
        description="kepco power supply 2",
        tangodevice=tango_base + "kepco/current2",
        fmtstr="%.3f",
    ),
    radial_coil2=device(
        "nicos.devices.entangle.PowerSupply",
        description="kepco power supply 3",
        tangodevice=tango_base + "kepco/current3",
        fmtstr="%.3f",
    ),
    axial_coil2=device(
        "nicos.devices.entangle.PowerSupply",
        description="kepco power supply 4",
        tangodevice=tango_base + "kepco/current4",
        fmtstr="%.3f",
    ),
    nutator1=device(
        "nicos.devices.generic.Axis",
        description="nutator 1 (facing sample)",
        motor=device(
            "nicos.devices.entangle.Motor",
            tangodevice=tango_base + "aircontrol/plc_nutator1_mot",
            fmtstr="%.4f",
            visibility=(),
        ),
        coder=device(
            "nicos.devices.entangle.Sensor",
            tangodevice=tango_base + "aircontrol/plc_nutator1_enc",
            fmtstr="%.4f",
            visibility=(),
        ),
        fmtstr="%.3f",
        precision=0.001,
    ),
    nutator2=device(
        "nicos.devices.generic.Axis",
        description="nutator 2 (facing analyser)",
        motor=device(
            "nicos.devices.entangle.Motor",
            tangodevice=tango_base + "aircontrol/plc_nutator2_mot",
            fmtstr="%.4f",
            visibility=(),
        ),
        coder=device(
            "nicos.devices.entangle.Sensor",
            tangodevice=tango_base + "aircontrol/plc_nutator2_enc",
            fmtstr="%.4f",
            visibility=(),
        ),
        fmtstr="%.3f",
        precision=0.001,
    ),
)

startupcode = """
radial_coil1.userlimits=(-2.1, 2.1)
axial_coil1.userlimits=(-2.1, 2.1)
radial_coil2.userlimits=(-2.1, 2.1)
axial_coil2.userlimits=(-2.1, 2.1)
"""
