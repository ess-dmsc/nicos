description = "Julabo FP50HL - Selene guide 2"

pv_root = "ESTIA:WtrC-TE-002:"

devices = dict(
    julabo_2_online=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Whether it is responsive",
        readpv=f"{pv_root}Online-R",
        visibility=(),
    ),
    julabo_2_remote_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Remote mode",
        readpv=f"{pv_root}Mode-R",
        writepv=f"{pv_root}Mode-S",
        visibility=(),
    ),
    julabo_2_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The temperature setpoint",
        readpv=f"{pv_root}TemperatureSP1-R",
        writepv=f"{pv_root}TemperatureSP1-S",
        targetpv=f"{pv_root}TemperatureSP1-S",
    ),
    julabo_2_internal_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The internal sensor temperature readout (bath)",
        readpv=f"{pv_root}Temperature-R",
    ),
    julabo_2_external_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The external sensor temperature readout (pt100)",
        readpv=f"{pv_root}TempExtSensor-R",
    ),
    julabo_2_external_mode=device(
        # The system actuates to make the selected sensor equals to the setpoint.
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Use external sensor for regulation instead of internal sensor",
        readpv=f"{pv_root}ExternalSensor-R",
        writepv=f"{pv_root}ExternalSensor-S",
    ),
    julabo_2_safety=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The safety sensor temperature",
        readpv=f"{pv_root}TempSafetySensor-R",
        visibility=(),
    ),
    julabo_2_temperature_high_limit=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high temp warning limit",
        readpv=f"{pv_root}TempHighLimit-R",
        writepv=f"{pv_root}TempHighLimit-S",
        visibility=(),
    ),
    julabo_2_temperature_low_limit=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The low temp warning limit",
        readpv=f"{pv_root}TempLowLimit-R",
        writepv=f"{pv_root}TempLowLimit-S",
        visibility=(),
    ),
    julabo_2_heating_power=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The heating power being used %",
        readpv=f"{pv_root}Power-R",
        visibility=(),
    ),
    julabo_2_max_cooling=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The maximum cooling power %",
        readpv=f"{pv_root}MaxCoolPower-R",
        writepv=f"{pv_root}MaxCoolPower-S",
        visibility=(),
    ),
    julabo_2_max_heating=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The maximum heating power %",
        readpv=f"{pv_root}MaxHeatPower-R",
        writepv=f"{pv_root}MaxHeatPower-S",
        visibility=(),
    ),
    julabo_2_internal_slope=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The internal slope",
        readpv=f"{pv_root}InternalSlope-R",
        visibility=(),
    ),
    julabo_2_status_message=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The status message",
        readpv=f"{pv_root}Status-R",
        visibility=(),
    ),
    julabo_2_version=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The software version",
        readpv=f"{pv_root}Version-R",
        visibility=(),
    ),
    julabo_2_pump_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The pump pressure controller",
        readpv=f"{pv_root}PumpPressure-R",
        writepv=f"{pv_root}PumpPressure-S",
    ),
)
