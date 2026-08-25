description = "Sample Environment Flow-Cryo"

pv_root = "ESTIA-SES:Cryo-TC-001:"

devices = dict(
    flow_cryo_summary=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Controller Alarm Status Summary",
        readpv=f"{pv_root}AlarmSummary",
        display_order=10,
    ),
    flow_cryo_state_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The temp warning limit",
        readpv=f"{pv_root}Disable",
        writepv=f"{pv_root}Disable",
        display_order=9,
    ),
    # Set High Temp Limit
    flow_cryo_high_temp_limit_A=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The temp warning limit",
        readpv=f"{pv_root}TempLimitA-RB",
        writepv=f"{pv_root}TempLimitA-SP",
    ),
    flow_cryo_high_temp_limit_B=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The temp warning limit",
        readpv=f"{pv_root}TempLimitB-RB",
        writepv=f"{pv_root}TempLimitB-SP",
    ),
    flow_cryo_high_temp_limit_C=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The temp warning limit",
        readpv=f"{pv_root}TempLimitC-RB",
        writepv=f"{pv_root}TempLimitC-SP",
    ),
    # Set Sensor Temp Units
    flow_cryo_high_units_A=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The temp warning limit",
        readpv=f"{pv_root}InTypeA-Units-RB",
        writepv=f"{pv_root}InTypeA-Units-SP",
    ),
    flow_cryo_high_units_B=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The temp warning limit",
        readpv=f"{pv_root}InTypeB-Units-RB",
        writepv=f"{pv_root}InTypeB-Units-SP",
    ),
    flow_cryo_high_units_C=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The temp warning limit",
        readpv=f"{pv_root}InTypeC-Units-RB",
        writepv=f"{pv_root}InTypeC-Units-SP",
    ),
)
