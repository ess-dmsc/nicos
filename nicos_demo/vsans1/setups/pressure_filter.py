description = "pressure filter readout"

group = "lowlevel"

devices = dict(
    p_in_filter=device(
        "nicos.devices.generic.VirtualMotor",
        description="pressure in front of filter",
        abslimits=(5.1, 5.1),
        curvalue=5.1,
        fmtstr="%.2f",
        loglevel="info",
        jitter=0.1,
        unit="bar",
        maxage=125,
        pollinterval=60,
    ),
    p_out_filter=device(
        "nicos.devices.generic.VirtualMotor",
        description="pressure behind of filter",
        abslimits=(5.0, 5.0),
        curvalue=5.0,
        fmtstr="%.2f",
        loglevel="info",
        jitter=0.1,
        unit="bar",
        maxage=125,
        pollinterval=60,
    ),
    p_diff_filter=device(
        "nicos.devices.generic.CalculatedReadable",
        description="pressure difference between in front and behind filter",
        device1="p_in_filter",
        device2="p_out_filter",
        op="-",
        fmtstr="%.2f",
        loglevel="info",
        maxage=125,
        pollinterval=60,
    ),
)
