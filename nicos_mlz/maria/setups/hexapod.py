description = "Hexapod control"
group = "optional"

excludes = []

tango_base = "tango://phys.maria.frm2:10000/maria/"
hexapod = tango_base + "hexapod/h_"
tango_s7 = tango_base + "FZJS7/"

devices = dict(
    detarm=device(
        "nicos_mlz.jcns.devices.hexapod.Motor",
        description="Hexapod detector arm",
        tangodevice=hexapod + "detarm",
        unit="deg",
        fmtstr="%.3f",
    ),
    omega=device(
        "nicos_mlz.jcns.devices.hexapod.Motor",
        description="Hexapod rotation table",
        tangodevice=hexapod + "omega",
        unit="deg",
        fmtstr="%.3f",
    ),
    t2t=device(
        "nicos_mlz.jcns.devices.motor.MasterSlaveMotor",
        description="2 theta axis moving detarm = 2 * omega",
        master="omega",
        slave="detarm",
        scale=2.0,
    ),
    rx=device(
        "nicos_mlz.jcns.devices.hexapod.Motor",
        description="Hexapod rotation around X",
        tangodevice=hexapod + "rx",
        unit="deg",
        fmtstr="%.3f",
    ),
    ry=device(
        "nicos_mlz.jcns.devices.hexapod.Motor",
        description="Hexapod rotation around Y",
        tangodevice=hexapod + "ry",
        unit="deg",
        fmtstr="%.3f",
    ),
    rz=device(
        "nicos_mlz.jcns.devices.hexapod.Motor",
        description="Hexapod rotation around Z",
        tangodevice=hexapod + "rz",
        unit="deg",
        fmtstr="%.3f",
    ),
    tx=device(
        "nicos_mlz.jcns.devices.hexapod.Motor",
        description="Hexapod translation in X",
        tangodevice=hexapod + "tx",
        unit="mm",
        fmtstr="%.2f",
    ),
    ty=device(
        "nicos_mlz.jcns.devices.hexapod.Motor",
        description="Hexapod translation in Y",
        tangodevice=hexapod + "ty",
        unit="mm",
        fmtstr="%.2f",
    ),
    tz=device(
        "nicos_mlz.jcns.devices.hexapod.Motor",
        description="Hexapod translation in Z",
        tangodevice=hexapod + "tz",
        unit="mm",
        fmtstr="%.2f",
    ),
)
