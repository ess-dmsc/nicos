devices = dict(
    temperature_sensor=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="estia-selpt100-001:Calc_out",
        statuspv="estia-selpt100-001:AnalogStatus",
        description="Temperature Sensor",
    ),
    axis=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-10, 10),
        curvalue=0,
        unit="mm",
        fmtstr="%.2f",
    ),
)
