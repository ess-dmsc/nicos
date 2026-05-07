description = "Julabo MAGIO-MS-1000F circulator (device 1)"

pv_root = "LOKI-SE:WtrC-TE-001:"

devices = dict(
    julabo_1_online=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Whether it is responsive",
        readpv=f"{pv_root}Online-R",
        visibility=(),
    ),
    julabo_1_remote_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Remote mode",
        readpv=f"{pv_root}Mode-R",
        writepv=f"{pv_root}Mode-S",
        visibility=(),
    ),
    julabo_1_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The temperature setpoint",
        readpv=f"{pv_root}TemperatureSP1-R",
        writepv=f"{pv_root}TemperatureSP1-S",
        targetpv=f"{pv_root}TemperatureSP1-S",
    ),
    julabo_1_internal_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The internal sensor temperature readout (bath)",
        readpv=f"{pv_root}Temperature-R",
    ),
    julabo_1_external_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The external sensor temperature readout (pt100)",
        readpv=f"{pv_root}TempExtSensor-R",
    ),
    julabo_1_external_enabled=device(
        # The system actuates to make the selected sensor equals to the setpoint.
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Use external sensor for regulation instead of internal sensor",
        readpv=f"{pv_root}ExternalSensor-R",
        writepv=f"{pv_root}ExternalSensor-S",
    ),
    julabo_1_safety=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The safety sensor temperature",
        readpv=f"{pv_root}TempSafetySensor-R",
        visibility=(),
    ),
    julabo_1_temperature_high_limit=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high temp warning limit",
        readpv=f"{pv_root}TempHighLimit-R",
        writepv=f"{pv_root}TempHighLimit-S",
        visibility=(),
    ),
    julabo_1_temperature_low_limit=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The low temp warning limit",
        readpv=f"{pv_root}TempLowLimit-R",
        writepv=f"{pv_root}TempLowLimit-S",
        visibility=(),
    ),
    julabo_1_heating_power=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The heating power being used %",
        readpv=f"{pv_root}Power-R",
        visibility=(),
    ),
    julabo_1_max_cooling=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The maximum cooling power %",
        readpv=f"{pv_root}MaxCoolPower-R",
        writepv=f"{pv_root}MaxCoolPower-S",
        visibility=(),
    ),
    julabo_1_max_heating=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The maximum heating power %",
        readpv=f"{pv_root}MaxHeatPower-R",
        writepv=f"{pv_root}MaxHeatPower-S",
        visibility=(),
    ),
    julabo_1_internal_slope=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The internal slope",
        readpv=f"{pv_root}InternalSlope-R",
        visibility=(),
    ),
    julabo_1_status_message=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The status message",
        readpv=f"{pv_root}StatusMsg-R",
        visibility=(),
    ),
    julabo_1_version=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The software version",
        readpv=f"{pv_root}Version-R",
        visibility=(),
    ),
)
