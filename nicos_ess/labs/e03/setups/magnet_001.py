description = "15T magnet MAG-001"

pv_root = "SE-MAG-001:"

devices = dict(
    regulation_temp=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Regulation temperature",
        readpv=f"{pv_root}VTI-r",
    ),
    heater_power=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Heater output power",
        readpv=f"{pv_root}VTI-HeaterPower-r",
    ),
    heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Heater 1 range",
        readpv=f"{pv_root}VTI-HtrRange-s",
        writepv=f"{pv_root}VTI-HtrRange-s",
    ),
    vti_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="VTI pressure",
        readpv=f"{pv_root}VTI-Pressure-r",
    ),
    vti_pressure_setpoint_percent=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="VTI pressure loop percent setpoint",
        readpv=f"{pv_root}VTI-NVopening-s",
        writepv=f"{pv_root}VTI-NVopening-s",
    ),
    vti_temp=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="VTI temperature",
        readpv=f"{pv_root}VTI-VTITemp-r",
    ),
    temp_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Temperature setpoint",
        readpv=f"{pv_root}VTI-tempSetpoint-s",
        writepv=f"{pv_root}VTI-tempSetpoint-s",
    ),
    vti_pressure_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="VTI pressure loop setpoint",
        readpv=f"{pv_root}VTI-pressure-s",
        writepv=f"{pv_root}VTI-pressure-s",
    ),
    vti_pressure_control=device(
        "nicos_ess.devices.epics.pva.EpicsStringMoveable",
        description="VTI pressure loop control on off. Permitted values: ON, OFF",
        readpv=f"{pv_root}VTI-flowControl-s",
        writepv=f"{pv_root}VTI-flowControl-s",
    ),
    mag_action=device(
        "nicos_ess.devices.epics.pva.EpicsStringMoveable",
        description="Action. Permitted values: HOLD, RTOS, RTOZ, CLMP",
        readpv=f"{pv_root}Magnet-action-s",
        writepv=f"{pv_root}Magnet-action-s",
    ),
    mag_switch_heater=device(
        "nicos_ess.devices.epics.pva.EpicsStringMoveable",
        description="Set switch heater. Permitted values: ON, OFF",
        readpv=f"{pv_root}Magnet-switchHeater-s",
        writepv=f"{pv_root}Magnet-switchHeater-s",
    ),
    nitrogen_level=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Nitrogen level",
        readpv=f"{pv_root}Magnet-LN2-r",
    ),
    helium_level=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Helium level",
        readpv=f"{pv_root}Magnet-LHe-r",
    ),
    mag_field_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Magnetic field setpoint",
        readpv=f"{pv_root}Magnet-FieldTarget-s",
        writepv=f"{pv_root}Magnet-FieldTarget-s",
    ),
    mag_current=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="mercuryips/current/Z",
        readpv=f"{pv_root}Magnet-Current-r",
    ),
    mag_persistent_field=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Persistent field",
        readpv=f"{pv_root}Magnet-PFLD-r",
    ),
    mag_psu_field=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Psu field",
        readpv=f"{pv_root}Magnet-psuField-r",
    ),
    mag_field_ramp_rate=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Magnetic field ramp rate",
        readpv=f"{pv_root}Magnet-fieldRamprate-s",
        writepv=f"{pv_root}Magnet-fieldRamprate-s",
    ),
    mag_ramp_rate=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Ramp rate",
        readpv=f"{pv_root}Magnet-ramprate-r",
    ),
    mag_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Magnet mode",
        readpv=f"{pv_root}Magnet-Magnet_mode-s",
        writepv=f"{pv_root}Magnet-Magnet_mode-s",
    ),
    mag_user_field_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The magnetic field requested by the user",
        readpv=f"{pv_root}Magnet-UserFieldTarget-s",
        writepv=f"{pv_root}Magnet-UserFieldTarget-s",
    ),
    mag_go=device(
        # bool
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Go",
        readpv=f"{pv_root}Magnet-go-s",
        writepv=f"{pv_root}Magnet-go-s",
    ),
    mag_voltage=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Voltage",
        readpv=f"{pv_root}Magnet-voltage-r",
    ),
    mag_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The status of the instance",
        readpv=f"{pv_root}Magnet-MAG-001status-s",
        writepv=f"{pv_root}Magnet-MAG-001status-s",
    ),
    sample_temp=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Sample temperature",
        readpv=f"{pv_root}Sample-Temp-r",
    ),
    sample_temp_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Temperature setpoint",
        readpv=f"{pv_root}Sample-Setpoint-s",
        writepv=f"{pv_root}Sample-Setpoint-s",
    ),
    sample_heater_power=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Heater output power",
        readpv=f"{pv_root}Sample-HeaterPower-r",
    ),
    sample_heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Heater range",
        readpv=f"{pv_root}Sample-HtrRange-s",
        writepv=f"{pv_root}Sample-HtrRange-s",
    ),
    mag_warning_field_off=device(
        # bool
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Magnet field off input 1 on moxa",
        readpv=f"{pv_root}warningLights-magnet_field_off-r",
    ),
    mag_warning_interlock=device(
        # bool
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Connector Interlock detached input 0 on moxa",
        readpv=f"{pv_root}warningLights-connector_interlock-r",
    ),
)
