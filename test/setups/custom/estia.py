devices = dict(
    temperature_sensor=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="estia-selpt100-001:Calc_out",
        statuspv="estia-selpt100-001:AnalogStatus",
        unit="C",
        description="Temperature Sensor",
    ),
    ih1=device(
        "nicos_ess.estia.devices.attocube.IDS3010Axis",
        axis=1,
        description="Test IF axis 1",
        readpv="ATTOCUBE:Axis1:Displacement_RBV",
        pvprefix="ATTOCUBE",
    ),
    ih2=device(
        "nicos_ess.estia.devices.attocube.IDS3010Axis",
        axis=2,
        description="Test IF axis 2",
        readpv="ATTOCUBE:Axis2:Displacement_RBV",
        pvprefix="ATTOCUBE",
    ),
    IDS3010=device(
        "nicos_ess.estia.devices.attocube.IDS3010Control",
        description="Attocube IDS3010 control",
        readpv="ATTOCUBE:CurrentMode_RBV",
        writepv="ATTOCUBE:StartStopMeasurement",
        pvprefix="ATTOCUBE",
    ),
    axis=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-10, 10),
        curvalue=0,
        unit="mm",
        fmtstr="%.2f",
    ),
    distance=device(
        "nicos_ess.estia.devices.attocube.MirrorDistance",
        axis="axis",
        description="MirrorDistance test device",
    ),
)
