description = "Julabo MAGIO-MS-1000F circulator (device 1)"

pv_root = "LOKI-SE:WtrC-TE-001:"

devices = dict(
    julabo_1_online=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Whether it is responsive",
        readpv="{}Online-R".format(pv_root),
        visibility=(),
    ),
    julabo_1_remote_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Remote mode",
        readpv="{}Mode-R".format(pv_root),
        writepv="{}Mode-S".format(pv_root),
        visibility=(),
    ),
    julabo_1_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The temperature setpoint",
        readpv="{}TemperatureSP1-R".format(pv_root),
        writepv="{}TemperatureSP1-S".format(pv_root),
        targetpv="{}TemperatureSP1-S".format(pv_root),
    ),
    julabo_1_internal_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The internal sensor temperature readout (bath)",
        readpv="{}Temperature-R".format(pv_root),
    ),
    julabo_1_external_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The external sensor temperature readout (pt100)",
        readpv="{}TempExtSensor-R".format(pv_root),
    ),
    julabo_1_external_enabled=device(
        # The system actuates to make the selected sensor equals to the setpoint.
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Use external sensor for regulation instead of internal sensor",
        readpv="{}ExternalSensor-R".format(pv_root),
        writepv="{}ExternalSensor-S".format(pv_root),
    ),
    julabo_1_safety=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The safety sensor temperature",
        readpv="{}TempSafetySensor-R".format(pv_root),
        visibility=(),
    ),
    julabo_1_temperature_high_limit=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high temp warning limit",
        readpv="{}TempHighLimit-R".format(pv_root),
        writepv="{}TempHighLimit-S".format(pv_root),
        visibility=(),
    ),
    julabo_1_temperature_low_limit=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The low temp warning limit",
        readpv="{}TempLowLimit-R".format(pv_root),
        writepv="{}TempLowLimit-S".format(pv_root),
        visibility=(),
    ),
    julabo_1_heating_power=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The heating power being used %",
        readpv="{}Power-R".format(pv_root),
        visibility=(),
    ),
    julabo_1_max_cooling=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The maximum cooling power %",
        readpv="{}MaxCoolPower-R".format(pv_root),
        writepv="{}MaxCoolPower-S".format(pv_root),
        visibility=(),
    ),
    julabo_1_max_heating=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The maximum heating power %",
        readpv="{}MaxHeatPower-R".format(pv_root),
        writepv="{}MaxHeatPower-S".format(pv_root),
        visibility=(),
    ),
    julabo_1_internal_slope=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The internal slope",
        readpv="{}InternalSlope-R".format(pv_root),
        visibility=(),
    ),
    julabo_1_status_message=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The status message",
        readpv="{}StatusMsg-R".format(pv_root),
        visibility=(),
    ),
    julabo_1_version=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The software version",
        readpv="{}Version-R".format(pv_root),
        visibility=(),
    ),
)
