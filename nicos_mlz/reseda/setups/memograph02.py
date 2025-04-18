description = "memograph02 readout"
group = "lowlevel"

tango_base = "tango://ictrlfs.ictrl.frm2.tum.de:10000/memograph02/RESEDA1/"

devices = dict(
    tap02_t_in=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling inlet temperature",
        tangodevice=tango_base + "T_in",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        warnlimits=(-1, 17.5),  # -1 no lower value
        unit="degC",
    ),
    tap02_t_out=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling outlet temperature",
        tangodevice=tango_base + "T_out",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        unit="degC",
    ),
    tap02_p_in=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling inlet pressure",
        tangodevice=tango_base + "P_in",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        unit="bar",
    ),
    tap02_p_out=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling outlet pressure",
        tangodevice=tango_base + "P_out",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        unit="bar",
    ),
    tap02_flow_in=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling inlet flow",
        tangodevice=tango_base + "FLOW_in",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        warnlimits=(0.2, 100),  # 100 no upper value
        unit="l/min",
    ),
    tap02_flow_out=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling outlet flow",
        tangodevice=tango_base + "FLOW_out",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        unit="l/min",
    ),
    tap02_leak=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling leakage",
        tangodevice=tango_base + "Leak",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        warnlimits=(-1, 1),  # -1 no lower value
        unit="l/min",
    ),
    tap02_cooling=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling power",
        tangodevice=tango_base + "Cooling",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        unit="kW",
    ),
)
