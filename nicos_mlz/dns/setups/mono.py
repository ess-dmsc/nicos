description = "DNS monochromator"
group = "lowlevel"

tango_base = "tango://phys.dns.frm2:10000/dns/"

devices = dict(
    mon_tilt=device(
        "nicos.devices.entangle.Motor",
        description="Monochromator tilt",
        tangodevice=tango_base + "s7_motor/mon_tilt",
        precision=1.0,
    ),
    mon_rot=device(
        "nicos.devices.entangle.Motor",
        description="Monochromator rotation",
        tangodevice=tango_base + "s7_motor/mon_rot",
        precision=0.05,
    ),
    m3l_rot=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal rotation",
        tangodevice=tango_base + "s7_motor/m3l_rot",
        precision=1.0,
    ),
    m2l_rot=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal rotation",
        tangodevice=tango_base + "s7_motor/m2l_rot",
        precision=1.0,
    ),
    m1l_rot=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal crystal rotation",
        tangodevice=tango_base + "s7_motor/m1l_rot",
        precision=1.0,
    ),
    m0_rot=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal crystal rotation",
        tangodevice=tango_base + "s7_motor/m0_rot",
        precision=1.0,
    ),
    m1r_rot=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal crystal rotation",
        tangodevice=tango_base + "s7_motor/m1r_rot",
        precision=1.0,
    ),
    m2r_rot=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal crystal rotation",
        tangodevice=tango_base + "s7_motor/m2r_rot",
        precision=1.0,
    ),
    m3r_rot=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal crystal rotation",
        tangodevice=tango_base + "s7_motor/m3r_rot",
        precision=1.0,
    ),
    beam_rot=device(
        "nicos.devices.entangle.Motor",
        description="Beam rotation",
        tangodevice=tango_base + "s7_motor/beam_rot",
        precision=1.0,
    ),
    mon_lambda=device(
        "nicos.devices.generic.ManualMove",
        description="Monochromator wavelength",
        abslimits=(2.4, 6),
        unit="A",
    ),
    ton_pos=device(
        "nicos.devices.entangle.AnalogInput",
        description="Angle of ton relative to neutron guide",
        tangodevice=tango_base + "s7_analog/ton_pos",
        visibility=(),
    ),
    ton_lambda=device(
        "nicos_mlz.dns.devices.mono.Wavelength",
        description="Wavelength derived from ton angle",
        angle="ton_pos",
    ),
    mccrystal_t1=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal tilt 1",
        tangodevice=tango_base + "s7_motor/DC_mccrystal_t1",
        precision=1.0,
    ),
    mccrystal_t2=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal tilt 2",
        tangodevice=tango_base + "s7_motor/DC_mccrystal_t2",
        precision=1.0,
    ),
    mccrystal_t3=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal tilt 3",
        tangodevice=tango_base + "s7_motor/DC_mccrystal_t3",
        precision=1.0,
    ),
    mccrystal_t4=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal tilt 4",
        tangodevice=tango_base + "s7_motor/DC_mccrystal_t4",
        precision=1.0,
    ),
    mccrystal_t5=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal tilt 5",
        tangodevice=tango_base + "s7_motor/DC_mccrystal_t5",
        precision=1.0,
    ),
    mccrystal_t6=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal tilt 6",
        tangodevice=tango_base + "s7_motor/DC_mccrystal_t6",
        precision=1.0,
    ),
    mccrystal_t7=device(
        "nicos.devices.entangle.Motor",
        description="MC-crystal tilt 7",
        tangodevice=tango_base + "s7_motor/DC_mccrystal_t7",
        precision=1.0,
    ),
)

extended = dict(
    representative="mon_lambda",
)
