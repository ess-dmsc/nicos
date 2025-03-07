description = "Sample table setup"

group = "lowlevel"

tango_base = "tango://phys.treff.frm2:10000/treff"
tango_s7 = tango_base + "/FZJS7/"

devices = dict(
    sample_x=device(
        "nicos.devices.entangle.MotorAxis",
        description="Sample table x translation",
        tangodevice=tango_s7 + "sample_x",
        precision=0.01,
        fmtstr="%.2f",
        unit="mm",
    ),
    sample_y=device(
        "nicos.devices.entangle.MotorAxis",
        description="Sample table y translation",
        tangodevice=tango_s7 + "sample_y",
        precision=0.01,
        fmtstr="%.2f",
        unit="mm",
    ),
    sample_z=device(
        "nicos.devices.entangle.MotorAxis",
        description="Sample table z translation",
        tangodevice=tango_s7 + "sample_z",
        precision=0.01,
        fmtstr="%.2f",
        unit="mm",
    ),
    omega=device(
        "nicos.devices.entangle.MotorAxis",
        description="Sample table omega rotation",
        tangodevice=tango_s7 + "omega",
        precision=0.005,
        fmtstr="%.3f",
        unit="deg",
    ),
    phi=device(
        "nicos.devices.entangle.MotorAxis",
        description="Sample table phi rotation",
        tangodevice=tango_s7 + "phi",
        precision=0.01,
        fmtstr="%.2f",
        unit="deg",
    ),
    chi=device(
        "nicos.devices.entangle.MotorAxis",
        description="Sample table chi rotation",
        tangodevice=tango_s7 + "chi",
        precision=0.01,
        fmtstr="%.2f",
        unit="deg",
    ),
    detarm=device(
        "nicos.devices.entangle.MotorAxis",
        description="Detector arm rotation angle",
        tangodevice=tango_s7 + "detector",
        precision=0.005,
        fmtstr="%.3f",
    ),
    t2t=device(
        "nicos_mlz.jcns.devices.motor.MasterSlaveMotor",
        description="2 theta axis moving detarm = 2 * omega",
        master="omega",
        slave="detarm",
        scale=2.0,
        fmtstr="%.3f %.3f",
    ),
)
