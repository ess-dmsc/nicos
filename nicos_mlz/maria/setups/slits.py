description = "Slits setup"
group = "optional"

includes = ["hexapod"]

tango_base = "tango://phys.maria.frm2:10000/maria"
tango_pi = tango_base + "/piaperture"
tango_s7 = tango_base + "/FZJS7"
tango_analog = tango_base + "/FZJDP_Analog"

devices = dict(
    s1_left=device(
        "nicos.devices.entangle.Motor",
        description="slit s1 left",
        tangodevice=tango_pi + "/s1_left",
        precision=0.001,
        fmtstr="%.3f",
    ),
    s1_right=device(
        "nicos.devices.entangle.Motor",
        description="slit s1 right",
        tangodevice=tango_pi + "/s1_right",
        precision=0.001,
        fmtstr="%.3f",
    ),
    s1_bottom=device(
        "nicos.devices.generic.Axis",
        description="slit s1 bottom",
        motor="s1_bottom_mot",
        obs="s1_bottom_cod",
        precision=0.4,
        fmtstr="%.1f",
    ),
    s1_bottom_mot=device(
        "nicos.devices.entangle.Motor",
        description="slit s1 bottom motor",
        tangodevice=tango_s7 + "/s1_bottom",
        precision=0.01,
        fmtstr="%.2f",
        unit="mm",
        visibility=(),
    ),
    s1_bottom_cod=device(
        "nicos.devices.entangle.Sensor",
        description="slit s1 bottom poti",
        tangodevice=tango_analog + "/s1_bottom",
        fmtstr="%.1f",
        unit="mm",
        pollinterval=5,
        maxage=6,
        visibility=(),
    ),
    s1_top=device(
        "nicos.devices.generic.Axis",
        description="slit s1 top",
        motor="s1_top_mot",
        obs="s1_top_cod",
        precision=0.4,
        fmtstr="%.1f",
    ),
    s1_top_mot=device(
        "nicos.devices.entangle.Motor",
        description="slit s1 top motor",
        tangodevice=tango_s7 + "/s1_top",
        precision=0.01,
        fmtstr="%.2f",
        unit="mm",
        visibility=(),
    ),
    s1_top_cod=device(
        "nicos.devices.entangle.Sensor",
        description="slit s1 top poti",
        tangodevice=tango_analog + "/s1_top",
        fmtstr="%.1f",
        unit="mm",
        pollinterval=5,
        maxage=6,
        visibility=(),
    ),
    s1=device(
        "nicos.devices.generic.Slit",
        description="Slit 1",
        left="s1_left",
        right="s1_right",
        bottom="s1_bottom",
        top="s1_top",
        opmode="centered",
        coordinates="opposite",
        parallel_ref=True,
    ),
    s2_left=device(
        "nicos.devices.entangle.Motor",
        description="slit s2 left",
        tangodevice=tango_pi + "/s2_left",
        precision=0.001,
    ),
    s2_right=device(
        "nicos.devices.entangle.Motor",
        description="slit s2 right",
        tangodevice=tango_pi + "/s2_right",
        precision=0.001,
        fmtstr="%.3f",
    ),
    s2_bottom=device(
        "nicos.devices.generic.Axis",
        description="slit s2 bottom",
        motor="s2_bottom_mot",
        obs="s2_bottom_cod",
        precision=0.08,
        fmtstr="%.2f",
    ),
    s2_bottom_mot=device(
        "nicos.devices.entangle.Motor",
        description="slit s2 bottom motor",
        tangodevice=tango_s7 + "/s2_bottom",
        precision=0.02,
        fmtstr="%.2f",
        unit="mm",
        visibility=(),
    ),
    s2_bottom_cod=device(
        "nicos.devices.entangle.Sensor",
        description="slit s2 bottom poti",
        tangodevice=tango_analog + "/s2_bottom",
        fmtstr="%.2f",
        unit="mm",
        pollinterval=5,
        maxage=6,
        visibility=(),
    ),
    s2_top=device(
        "nicos.devices.generic.Axis",
        description="slit s2 top",
        motor="s2_top_mot",
        obs="s2_top_cod",
        precision=0.08,
        fmtstr="%.2f",
    ),
    s2_top_mot=device(
        "nicos.devices.entangle.Motor",
        description="slit s2 top motor",
        tangodevice=tango_s7 + "/s2_top",
        precision=0.02,
        fmtstr="%.2f",
        unit="mm",
        visibility=(),
    ),
    s2_top_cod=device(
        "nicos.devices.entangle.Sensor",
        description="slit s2 top poti",
        tangodevice=tango_analog + "/s2_top",
        fmtstr="%.2f",
        unit="mm",
        pollinterval=5,
        maxage=6,
        visibility=(),
    ),
    s2=device(
        "nicos.devices.generic.Slit",
        description="Slit 2",
        left="s2_left",
        right="s2_right",
        bottom="s2_bottom",
        top="s2_top",
        opmode="centered",
        coordinates="opposite",
        parallel_ref=True,
    ),
    ds_left=device(
        "nicos.devices.entangle.Motor",
        description="detector slit left",
        tangodevice=tango_s7 + "/ds_left",
        precision=0.001,
        fmtstr="%.3f",
    ),
    ds_right=device(
        "nicos.devices.entangle.Motor",
        description="detector slit right",
        tangodevice=tango_s7 + "/ds_right",
        precision=0.001,
        fmtstr="%.3f",
    ),
    ds_bottom=device(
        "nicos.devices.generic.VirtualMotor",
        description="virtual detector slit bottom motor",
        abslimits=(-75, 65),
        unit="mm",
        speed=0,
        visibility=(),
    ),
    ds_top=device(
        "nicos.devices.generic.VirtualMotor",
        description="virtual detector slit bottom motor",
        abslimits=(-75, 65),
        unit="mm",
        speed=0,
        visibility=(),
    ),
    ds=device(
        "nicos.devices.generic.Slit",
        description="detector slits",
        left="ds_left",
        right="ds_right",
        bottom="ds_bottom",
        top="ds_top",
        opmode="offcentered",
        coordinates="opposite",
        parallel_ref=True,
    ),
    footprint=device(
        "nicos_mlz.maria.devices.sampleillumination.SampleIllumination",
        description="Beam footprint",
        s1pos=4100,
        s2pos=400,
        s1="s1",
        s2="s1",
        theta="omega",
        unit="mm",
    ),
)
