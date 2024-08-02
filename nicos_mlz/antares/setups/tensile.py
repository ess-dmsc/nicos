description = "Tensile machine"

group = "optional"

nameservice = "antaresctrl.antares.frm2.tum.de"

devices = dict(
    teload=device(
        "nicos.devices.vendor.caress.Motor",
        description="load value of the tensile machine",
        nameserver="%s" % (nameservice,),
        config="TELOAD 500 TensileLoad.ControllableDevice",
        absdev=False,
        abslimits=(-50000, 50000),
        unit="N",
        fmtstr="%.2f",
        toolpath="/control/bin",
        caresspath="/control/bin",
    ),
    tepos=device(
        "nicos.devices.vendor.caress.Motor",
        description="position value of the tensile machine",
        nameserver="%s" % (nameservice,),
        config="TEPOS 500 TensilePos.ControllableDevice",
        absdev=False,
        abslimits=(0, 70),
        unit="mm",
        fmtstr="%.3f",
        toolpath="/control/bin",
        caresspath="/control/bin",
    ),
    teext=device(
        "nicos.devices.vendor.caress.Motor",
        description="extension value of the tensile machine",
        nameserver="%s" % (nameservice,),
        config="TEEXT 500 TensileExt.ControllableDevice",
        absdev=False,
        abslimits=(-3000, 3000),
        unit="um",
        fmtstr="%.3f",
        toolpath="/control/bin",
        caresspath="/control/bin",
    ),
)

display_order = 40
