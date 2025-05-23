description = "memograph readout"

group = "lowlevel"

# tango_base = 'tango://ictrlfs.ictrl.frm2.tum.de:10000/memograph03/SANS1/'

devices = dict(
    t_in_memograph=device(
        "nicos.devices.generic.VirtualCoder",
        description="Cooling inlet temperature",
        motor=device(
            "nicos.devices.generic.VirtualTemperature",
            setpoint=6,
            abslimits=(5, 15),
            unit="degC",
        ),
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        warnlimits=(-1, 17.5),  # -1 no lower value
        unit="degC",
    ),
    t_out_memograph=device(
        "nicos.devices.generic.VirtualCoder",
        description="Cooling outlet temperature",
        motor=device(
            "nicos.devices.generic.VirtualTemperature",
            setpoint=30,
            abslimits=(30, 50),
            unit="degC",
        ),
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        unit="degC",
    ),
    p_in_memograph=device(
        "nicos.devices.generic.VirtualCoder",
        description="Cooling inlet pressure",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        unit="bar",
    ),
    p_out_memograph=device(
        "nicos.devices.generic.VirtualCoder",
        description="Cooling outlet pressure",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        unit="bar",
    ),
    flow_in_memograph=device(
        "nicos.devices.generic.VirtualCoder",
        description="Cooling inlet flow",
        motor=device(
            "nicos.devices.generic.VirtualMotor",
            abslimits=(10, 100),
            curvalue=20,
            jitter=0.1,
            unit="l/min",
        ),
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        warnlimits=(0.2, 100),  # 100 no upper value
        unit="l/min",
    ),
    flow_out_memograph=device(
        "nicos.devices.generic.VirtualCoder",
        description="Cooling outlet flow",
        motor=device(
            "nicos.devices.generic.VirtualMotor",
            abslimits=(10, 100),
            curvalue=19.8,
            jitter=0.1,
            unit="l/min",
        ),
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        unit="l/min",
    ),
    leak_memograph=device(
        "nicos.devices.generic.analog.CalculatedReadable",
        description="Cooling leakage",
        device1="flow_in_memograph",
        device2="flow_out_memograph",
        op="-",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        warnlimits=(-1, 1),  # -1 no lower value
        unit="l/min",
    ),
    cooling_memograph=device(
        "nicos.devices.generic.analog.CalculatedReadable",
        description="Cooling power",
        device1="t_out_memograph",
        device2="t_in_memograph",
        op="-",
        pollinterval=30,
        maxage=60,
        fmtstr="%.2f",
        unit="kW",
    ),
)
