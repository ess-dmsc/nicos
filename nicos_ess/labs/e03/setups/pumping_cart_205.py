description = "Setup for SE-AUX-205 PVs with NICOS mapping."

pv_root = "SE:SE-AUX-205:"

devices = dict(
    # ------------------------------------------------------------------
    # Lakeshore temperatures
    # ------------------------------------------------------------------
    pc205_reg_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Lakeshore temperature channel A (regulator)",
        readpv=f"{pv_root}TempA-r",
    ),
    pc205_sample_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Lakeshore temperature channel B (sample)",
        readpv=f"{pv_root}TempB-r",
    ),
    pc205_lakeshore_temp_c=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Lakeshore temperature channel C",
        readpv=f"{pv_root}TempC-r",
    ),
    pc205_lakeshore_temp_d=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Lakeshore temperature channel D",
        readpv=f"{pv_root}TempD-r",
    ),
    # ------------------------------------------------------------------
    # Vacuum transducers on the pumping cart
    # ------------------------------------------------------------------
    pc205_pressure_sensor_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Vacuum transducer 1 (pumping cart 205)",
        readpv=f"{pv_root}P1-r",
    ),
    pc205_pressure_sensor_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Vacuum transducer 2 (pumping cart 205)",
        readpv=f"{pv_root}P2-r",
    ),
    # ------------------------------------------------------------------
    # Nitrogen level and filling control
    # ------------------------------------------------------------------
    pc205_ln2_level=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Liquid-nitrogen level",
        readpv=f"{pv_root}LN2-r",
    ),
    pc205_ln2f_fill_switch=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Start/stop LN2 fill",
        readpv=f"{pv_root}LN2F-Fill-s",
        writepv=f"{pv_root}LN2F-Fill-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    pc205_ln2f_auto_switch=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="LN2 auto-fill on/off",
        readpv=f"{pv_root}LN2F-Auto-s",
        writepv=f"{pv_root}LN2F-Auto-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    pc205_ln2f_state=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="State of the LN2 filling state machine",
        readpv=f"{pv_root}LN2F-State-r",
    ),
    pc205_ln2f_activity=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="LN2 filling in progress",
        readpv=f"{pv_root}LN2F-r",
    ),
    # ------------------------------------------------------------------
    # Flush cycle
    # ------------------------------------------------------------------
    pc205_flush_switch=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Start/stop the Flush cycle",
        readpv=f"{pv_root}Flush-s",
        writepv=f"{pv_root}Flush-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    pc205_flush_state=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Current state of the Flush state machine",
        readpv=f"{pv_root}Flush-State-r",
    ),
    # ------------------------------------------------------------------
    # Cold valve
    # ------------------------------------------------------------------
    pc205_cvalve_position=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cold valve current position",
        readpv=f"{pv_root}CValve-r",
    ),
    pc205_cvalve_target=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Cold valve target position",
        readpv=f"{pv_root}CValve-Target-s",
        writepv=f"{pv_root}CValve-Target-s",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    # ------------------------------------------------------------------
    # Pressure-regulator set-point
    # ------------------------------------------------------------------
    pc205_p_reg_pressure_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Pressure-regulator pressure set point",
        readpv=f"{pv_root}PReg-PSP-s",
        writepv=f"{pv_root}PReg-PSP-s",
        abslimits=(0, 1100),
        userlimits=(0, 1100),
        precision=0.1,
    ),
    # ------------------------------------------------------------------
    # Regulator-heater channels
    # ------------------------------------------------------------------
    pc205_reg_heater_power=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Regulator heater power (readback)",
        readpv=f"{pv_root}reg-htr-r",
    ),
    pc205_reg_heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Regulator heater range",
        readpv=f"{pv_root}reg-htr_range-s",
        writepv=f"{pv_root}reg-htr_range-s",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    pc205_reg_heater_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Regulator heater set point",
        readpv=f"{pv_root}reg-setpoint-s",
        writepv=f"{pv_root}reg-setpoint-s",
        abslimits=(0, 1000),
        userlimits=(0, 1000),
    ),
    # ------------------------------------------------------------------
    # Sample-heater channels
    # ------------------------------------------------------------------
    pc205_sample_heater_power=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Sample heater power (readback)",
        readpv=f"{pv_root}sample-htr-r",
    ),
    pc205_sample_heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Sample heater range",
        readpv=f"{pv_root}sample-htr_range-s",
        writepv=f"{pv_root}sample-htr_range-s",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    pc205_sample_heater_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Sample heater set point",
        readpv=f"{pv_root}sample-setpoint-s",
        writepv=f"{pv_root}sample-setpoint-s",
        abslimits=(0, 1000),
        userlimits=(0, 1000),
    ),
)
