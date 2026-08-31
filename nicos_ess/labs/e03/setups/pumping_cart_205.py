description = "Setup for SE-AUX-205 PVs with NICOS mapping."

pv_root = "se-aux-205:"

devices = dict(
    # ------------------------------------------------------------------
    # Lakeshore temperatures
    # ------------------------------------------------------------------
    regulator_temp=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Lakeshore temperature channel A (regulator)",
        readpv=f"{pv_root}tempA-r",
    ),
    sample_temp=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Lakeshore temperature channel B (sample)",
        readpv=f"{pv_root}TempB-r",
    ),
    channel_c_temp=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Lakeshore temperature channel C",
        readpv=f"{pv_root}TempC-r",
    ),
    channel_d_temp=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Lakeshore temperature channel D",
        readpv=f"{pv_root}TempD-r",
    ),
    # ------------------------------------------------------------------
    # Vacuum transducers on the pumping cart
    # ------------------------------------------------------------------
    pressure_sensor_1=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Vacuum transducer 1",
        readpv=f"{pv_root}P1-r",
    ),
    pressure_sensor_2=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Vacuum transducer 2",
        readpv=f"{pv_root}P2-r",
    ),
    # ------------------------------------------------------------------
    # Nitrogen level and filling control
    # ------------------------------------------------------------------
    nitrogen_level=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Liquid-nitrogen level",
        readpv=f"{pv_root}LN2-r",
    ),
    nitrogen_start_fill=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Start LN2 fill",
        readpv=f"{pv_root}LN2F-Fill-s",
        writepv=f"{pv_root}LN2F-Fill-s",
        visibility=(),
    ),
    nitrogen_auto_switch=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="LN2 auto-fill on/off",
        readpv=f"{pv_root}LN2F-Auto-s",
        writepv=f"{pv_root}LN2F-Auto-s",
        visibility=(),
    ),
    nitrogen_state=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="State of the LN2 filling state machine",
        readpv=f"{pv_root}LN2F-State-r",
        visibility=(),
    ),
    nitrogen_activity=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="LN2 filling in progress",
        readpv=f"{pv_root}LN2F-Filling-r",
    ),
    # ------------------------------------------------------------------
    # Flush cycle
    # ------------------------------------------------------------------
    flush_state=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Current state of the Flush state machine",
        readpv=f"{pv_root}Flush-State-r",
        visibility=(),
    ),
    flush_pressure_target=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Pressure target",
        readpv=f"{pv_root}MISSING!!!",
        writepv=f"{pv_root}MISSING!!!",
        visibility=(),
    ),
    flush_running=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Flush cycle is running",
        readpv=f"{pv_root}MISSING!!!",
        visibility=(),
    ),
    # ------------------------------------------------------------------
    # Cold valve
    # ------------------------------------------------------------------
    c_valve_position=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Cold valve current position",
        readpv=f"{pv_root}CValve-r",
    ),
    c_valve_target=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Cold valve target position",
        readpv=f"{pv_root}CValve-Target-s",
        writepv=f"{pv_root}CValve-Target-s",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    # ------------------------------------------------------------------
    # Regulator-heater channels
    # ------------------------------------------------------------------
    regulator_heater_power=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Regulator heater power (readback)",
        readpv=f"{pv_root}reg-htr-r",
    ),
    regulator_heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsDigitalMoveable",
        description="Regulator heater range",
        readpv=f"{pv_root}reg-htr_range-s",
        writepv=f"{pv_root}reg-htr_range-s",
    ),
    regulator_temp_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Regulator temperature setpoint",
        readpv=f"{pv_root}reg-setpoint-s",
        writepv=f"{pv_root}reg-setpoint-s",
        abslimits=(0, 1500),
        userlimits=(0, 1500),
    ),
    # ------------------------------------------------------------------
    # Sample-heater channels
    # ------------------------------------------------------------------
    sample_heater_power=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Sample heater power (readback)",
        readpv=f"{pv_root}sample-htr-r",
    ),
    sample_heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsDigitalMoveable",
        description="Sample heater range",
        readpv=f"{pv_root}sample-htr_range-s",
        writepv=f"{pv_root}sample-htr_range-s",
        abslimits=(0, 16777216),
        userlimits=(0, 16777216),
    ),
    sample_temp_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Sample temperature setpoint",
        readpv=f"{pv_root}sample-setpoint-s",
        writepv=f"{pv_root}sample-setpoint-s",
        abslimits=(0, 1500),
        userlimits=(0, 1500),
    ),
    # ------------------------------------------------------------------
    # Loop 1
    # ------------------------------------------------------------------
    loop_1_pid_p=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="PID proportional term for control loop 1",
        readpv=f"{pv_root}temp_loop_1-pid_p-s",
        writepv=f"{pv_root}temp_loop_1-pid_p-s",
        visibility=(),
    ),
    loop_1_pid_d=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="PID derivative term for control loop 1",
        readpv=f"{pv_root}temp_loop_1-pid_d-s",
        writepv=f"{pv_root}temp_loop_1-pid_d-s",
        visibility=(),
    ),
    loop_1_pid_i=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="PID integral term for control loop 1",
        readpv=f"{pv_root}temp_loop_1-pid_i-s",
        writepv=f"{pv_root}temp_loop_1-pid_i-s",
        visibility=(),
    ),
    loop_1_temp_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Closed-loop setpoint for output 1 in kelvin",
        readpv=f"{pv_root}temp_loop_1-setpoint-s",
        writepv=f"{pv_root}temp_loop_1-setpoint-s",
    ),
    loop_1_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Operating mode for output 1",
        readpv=f"{pv_root}:temp_loop_1-mode-s",
        writepv=f"{pv_root}:temp_loop_1-mode-s",
        visibility=(),
    ),
    # ------------------------------------------------------------------
    # Loop 2
    # ------------------------------------------------------------------
    loop_2_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Operating mode for output 2",
        readpv=f"{pv_root}:temp_loop_2-mode-s",
        writepv=f"{pv_root}:temp_loop_2-mode-s",
        visibility=(),
    ),
)
