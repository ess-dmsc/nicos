description = "Julabo FP50HE - Solid Liquid Sample Changer"

pv_root = "ESTIA-SES:WtrC-TE-001:"

devices = dict(
    slsc_julabo_online=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Whether it is responsive",
        readpv=f"{pv_root}Online-R",
        visibility=(),
    ),
    slsc_julabo_remote_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Remote mode",
        readpv=f"{pv_root}Mode-R",
        writepv=f"{pv_root}Mode-S",
        visibility=(),
    ),
    slsc_julabo_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The temperature setpoint",
        readpv=f"{pv_root}TemperatureSP1-R",
        writepv=f"{pv_root}TemperatureSP1-S",
        targetpv=f"{pv_root}TemperatureSP1-S",
    ),
    slsc_julabo_internal_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The internal sensor temperature readout (bath)",
        readpv=f"{pv_root}Temperature-R",
    ),
    slsc_julabo_external_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The external sensor temperature readout (pt100)",
        readpv=f"{pv_root}TempExtSensor-R",
    ),
    slsc_julabo_external_mode=device(
        # The system actuates to make the selected sensor equals to the setpoint.
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Use external sensor for regulation instead of internal sensor",
        readpv=f"{pv_root}ExternalSensor-R",
        writepv=f"{pv_root}ExternalSensor-S",
    ),
    slsc_julabo_safety=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The safety sensor temperature",
        readpv=f"{pv_root}TempSafetySensor-R",
        visibility=(),
    ),
    slsc_julabo_temperature_high_limit=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high temp warning limit",
        readpv=f"{pv_root}TempHighLimit-R",
        writepv=f"{pv_root}TempHighLimit-S",
        visibility=(),
    ),
    slsc_julabo_temperature_low_limit=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The low temp warning limit",
        readpv=f"{pv_root}TempLowLimit-R",
        writepv=f"{pv_root}TempLowLimit-S",
        visibility=(),
    ),
    slsc_julabo_heating_power=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The heating power being used %",
        readpv=f"{pv_root}Power-R",
        visibility=(),
    ),
    slsc_julabo_max_cooling=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The maximum cooling power %",
        readpv=f"{pv_root}MaxCoolPower-R",
        writepv=f"{pv_root}MaxCoolPower-S",
        visibility=(),
    ),
    slsc_julabo_max_heating=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The maximum heating power %",
        readpv=f"{pv_root}MaxHeatPower-R",
        writepv=f"{pv_root}MaxHeatPower-S",
        visibility=(),
    ),
    slsc_julabo_internal_slope=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The internal slope",
        readpv=f"{pv_root}InternalSlope-R",
        visibility=(),
    ),
    slsc_julabo_status_message=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The status message",
        readpv=f"{pv_root}Status-R",
        visibility=(),
    ),
    slsc_julabo_version=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The software version",
        readpv=f"{pv_root}Version-R",
        visibility=(),
    ),
    slsc_julabo_pump_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The pump pressure controller",
        readpv=f"{pv_root}PumpPressure-R",
        writepv=f"{pv_root}PumpPressure-S",
    ),
)
