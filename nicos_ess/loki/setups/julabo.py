description = "Julabo MAGIO-MS-1000F circulators"

# TODO: Add Julabo 1
pv_root = "LOKI-SE:WtrC-TE-002:"

devices = dict(
    # Online?
    julabo_002_online=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Whether it is responsive",
        readpv="{}Online-R".format(pv_root),
        visibility=(),
    ),
    # Mode
    julabo_002_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Mode",
        readpv="{}Mode-R".format(pv_root),
        writepv="{}Mode-S".format(pv_root),
    ),
    # 1 and 2 - Internal temperature
    julabo_002_T=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The internal temperature (readout and setpoint)",
        readpv="{}Temperature-R".format(pv_root),
        writepv="{}TemperatureSP1-S".format(pv_root),
        targetpv="{}TemperatureSP1-R".format(pv_root),
        abslimits=(-1e308, 1e308),
    ),
    # 3 - External temperature readout
    julabo_002_external_T=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The external sensor temperature (readout)",
        readpv="{}TempExtSensor-R".format(pv_root),
    ),
    # 4 - Use external sensor for regulation (is this already available?)
    julabo_002_external_enabled=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Use external sensor for regulation instead of internal sensor",
        readpv="{}ExternalSensor-R".format(pv_root),
        writepv="{}ExternalSensor-S".format(pv_root),
    ),
    # Safety sensor
    julabo_002_safety=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The safety sensor temperature",
        readpv="{}TempSafetySensor-R".format(pv_root),
        visibility=(),
    ),
    # Temp limits
    julabo_002_high_limit=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The high temp warning limit",
        readpv="{}TempHighLimit-R".format(pv_root),
        writepv="{}TempHighLimit-S".format(pv_root),
        visibility=(),
        abslimits=(-1e308, 1e308),
    ),
    julabo_002_low_limit=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The low temp warning limit",
        readpv="{}TempLowLimit-R".format(pv_root),
        writepv="{}TempLowLimit-S".format(pv_root),
        visibility=(),
        abslimits=(-1e308, 1e308),
    ),
    # Power and its limits
    julabo_002_heating_power=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The heating power being used %",
        readpv="{}Power-R".format(pv_root),
        visibility=(),
    ),
    julabo_002_max_cooling=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The maximum cooling power %",
        readpv="{}MaxCoolPower-R".format(pv_root),
        writepv="{}MaxCoolPower-S".format(pv_root),
        visibility=(),
        abslimits=(-1e308, 1e308),
    ),
    julabo_002_max_heating=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The maximum heating power %",
        readpv="{}MaxHeatPower-R".format(pv_root),
        writepv="{}MaxHeatPower-S".format(pv_root),
        visibility=(),
        abslimits=(-1e308, 1e308),
    ),
    # Slope
    julabo_002_internal_slope=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The internal slope",
        readpv="{}InternalSlope-R".format(pv_root),
        visibility=(),
    ),
    # Internal PID
    julabo_002_internal_P=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The internal P value",
        readpv="{}IntP-R".format(pv_root),
        writepv="{}IntP-S".format(pv_root),
        visibility=(),
        abslimits=(-1e308, 1e308),
    ),
    julabo_002_internal_I=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The internal I value",
        readpv="{}IntI-R".format(pv_root),
        writepv="{}IntI-S".format(pv_root),
        visibility=(),
        abslimits=(-1e308, 1e308),
    ),
    julabo_002_internal_D=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The internal D value",
        readpv="{}IntD-S".format(pv_root),
        writepv="{}IntD-S".format(pv_root),
        visibility=(),
        abslimits=(-1e308, 1e308),
    ),
    # External PID
    julabo_002_external_P=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The external P value",
        readpv="{}ExtP-R".format(pv_root),
        writepv="{}ExtP-S".format(pv_root),
        visibility=(),
        abslimits=(-1e308, 1e308),
    ),
    julabo_002_external_I=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The external I value",
        readpv="{}ExtI-R".format(pv_root),
        writepv="{}ExtI-S".format(pv_root),
        visibility=(),
        abslimits=(-1e308, 1e308),
    ),
    julabo_002_external_D=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The external D value",
        readpv="{}ExtD-R".format(pv_root),
        writepv="{}ExtD-S".format(pv_root),
        visibility=(),
        abslimits=(-1e308, 1e308),
    ),
    # More, debug
    julabo_002_status=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The status number",
        readpv="{}StatusNumber-R".format(pv_root),
        visibility=(),
    ),
    julabo_002_version=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The software version",
        readpv="{}Version-R".format(pv_root),
        visibility=(),
    ),
    julabo_002_barcode=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The unique model number",
        readpv="{}Barcode-R".format(pv_root),
        visibility=(),
    ),
)
