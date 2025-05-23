description = "memograph readout"

group = "optional"
tango_base = "tango://ictrlfs.ictrl.frm2.tum.de:10000/memograph09/NSE/"

devices = dict(
    cooling_t_in=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling inlet temperature",
        tangodevice=tango_base + "T_in",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        warnlimits=(-1, 17.5),  # -1 no lower value
    ),
    cooling_t_out=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling outlet temperature",
        tangodevice=tango_base + "T_out",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
    ),
    cooling_p_in=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling inlet pressure",
        tangodevice=tango_base + "P_in",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
    ),
    cooling_p_out=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling outlet pressure",
        tangodevice=tango_base + "P_out",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
    ),
    cooling_flow_in=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling inlet flow",
        tangodevice=tango_base + "FLOW_in",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        warnlimits=(0.2, 100),  # 100 no upper value
    ),
    cooling_power=device(
        "nicos.devices.entangle.Sensor",
        description="Cooling power",
        tangodevice=tango_base + "Cooling",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
    ),
)
