description = "DNS sample table and aperture"
group = "lowlevel"

tango_base = "tango://phys.dns.frm2:10000/dns/"

devices = dict(
    det_rot=device(
        "nicos.devices.entangle.MotorAxis",
        description="Detector bench rotation",
        tangodevice=tango_base + "s7_motor/det_rot",
        precision=0.03,
    ),
    ap_sam_x_left=device(
        "nicos.devices.entangle.MotorAxis",
        description="Aperture sample x left",
        tangodevice=tango_base + "s7_motor/ap_sam_x_left",
        precision=1.0,
    ),
    ap_sam_x_right=device(
        "nicos.devices.entangle.MotorAxis",
        description="Aperture sample x right",
        tangodevice=tango_base + "s7_motor/ap_sam_x_right",
        precision=1.0,
    ),
    ap_sam_y_upper=device(
        "nicos.devices.entangle.MotorAxis",
        description="Aperture sample y upper",
        tangodevice=tango_base + "s7_motor/ap_sam_y_upper",
        precision=1.0,
    ),
    ap_sam_y_lower=device(
        "nicos.devices.entangle.MotorAxis",
        description="Aperture sample y lower",
        tangodevice=tango_base + "s7_motor/ap_sam_y_lower",
        precision=1.0,
    ),
    sample_slit=device(
        "nicos.devices.generic.Slit",
        description="Aperture sample slit",
        left="ap_sam_x_left",
        right="ap_sam_x_right",
        bottom="ap_sam_y_lower",
        top="ap_sam_y_upper",
        pollinterval=5,
        maxage=10,
        coordinates="equal",
        opmode="offcentered",
    ),
    sample_rot=device(
        "nicos.devices.entangle.MotorAxis",
        description="Sample rotation",
        tangodevice=tango_base + "s7_motor/sample_rot",
        precision=0.01,
    ),
    cradle_up=device(
        "nicos.devices.entangle.Motor",
        description="Cradle up (phi)",
        tangodevice=tango_base + "s7_motor/cradle_up",
        precision=1.0,
    ),
    cradle_lo=device(
        "nicos.devices.entangle.Motor",
        description="Cradle low (chi)",
        tangodevice=tango_base + "s7_motor/cradle_lo",
        precision=1.0,
    ),
    virtual=device(
        "nicos.devices.generic.VirtualMotor",
        description="Virtual motor for cont. time scans",
        abslimits=(-1e6, 1e6),
        speed=0,
        unit="",
    ),
)
