description = "elliptical neutron guide nose"

group = "optional"

tango_base = "tango://ng-focus.toftof.frm2.tum.de:10000/box/"

devices = dict(
    ng_left=device(
        "nicos.devices.entangle.Motor",
        description="Left mirror bender of the flexible neutron guide",
        tangodevice=tango_base + "piezo/left",
        fmtstr="%.0f",
        abslimits=(-20000.0, 20000.0),
        requires={"level": "admin"},
    ),
    ng_left_sw=device(
        "nicos.devices.entangle.DigitalInput",
        description="Limit switch of the left motor",
        tangodevice=tango_base + "piface/sw_left",
        fmtstr="%d",
        visibility=(),
    ),
    ng_right=device(
        "nicos.devices.entangle.Motor",
        description="Right mirror bender of the flexible neutron guide",
        tangodevice=tango_base + "piezo/right",
        fmtstr="%.0f",
        abslimits=(-20000.0, 20000.0),
        requires={"level": "admin"},
    ),
    ng_right_sw=device(
        "nicos.devices.entangle.DigitalInput",
        description="Limit switch of the right motor",
        tangodevice=tango_base + "piface/sw_right",
        fmtstr="%d",
        visibility=(),
    ),
    ng_bottom=device(
        "nicos.devices.entangle.Motor",
        description="Bottom mirror bender of the flexible neutron guide",
        tangodevice=tango_base + "piezo/bottom",
        fmtstr="%.0f",
        abslimits=(-20000.0, 20000.0),
        requires={"level": "admin"},
    ),
    ng_bottom_sw=device(
        "nicos.devices.entangle.DigitalInput",
        description="Limit switch of the bottom motor",
        tangodevice=tango_base + "piface/sw_bottom",
        fmtstr="%d",
        visibility=(),
    ),
    ng_top=device(
        "nicos.devices.entangle.Motor",
        description="Top mirror bender of the flexible neutron guide",
        tangodevice=tango_base + "piezo/top",
        fmtstr="%.0f",
        abslimits=(-20000.0, 20000.0),
        requires={"level": "admin"},
    ),
    ng_top_sw=device(
        "nicos.devices.entangle.DigitalInput",
        description="Limit switch of the top motor",
        tangodevice=tango_base + "piface/sw_top",
        fmtstr="%d",
        visibility=(),
    ),
    ng_focus=device(
        "nicos.devices.generic.Slit",
        description="Focussing neutron guide",
        left="ng_left",
        right="ng_right",
        bottom="ng_bottom",
        top="ng_top",
        opmode="4blades",
        pollinterval=5,
        maxage=10,
        fmtstr="%.0f %.0f %.0f %.0f",
        requires={"level": "admin"},
    ),
)
