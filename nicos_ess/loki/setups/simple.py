description = "The motors for alignment in the YMIR cave"

devices = dict(
    mXY=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Single axis positioner",
        motorpv="IOC:m1",
        has_errorbit=False,
        has_reseterror=False,
        has_powerauto=False,
        has_msgtxt=False,
    ),
    sample_area_vacuum_valve_closed=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Vacuum valve - PLC",
        readpv="SIMPLE:MBBI",
        visibility={"namespace", "devlist", "metadata"},
    ),
    st_x = device('nicos.devices.generic.DeviceAlias',
        alias = 'sample_area_vacuum_value_closed',
    ),
    foo=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Vacuum valve - PLC",
        readpv="SIMPLE:VALUE1",
        writepv="SIMPLE:VALUE1",
        targetpv="SIMPLE:VALUE1",
        visibility={"namespace", "devlist", "metadata"},
    ),
)
