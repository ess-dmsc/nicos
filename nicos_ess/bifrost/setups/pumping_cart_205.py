description = "Setup for SE-AUX-205 PVs with NICOS mapping."

pv_root = "SE:SE-AUX-205:"

devices = dict(
    # ------------------------------------------------------------------
    # Lakeshore temperatures
    # ------------------------------------------------------------------
    regulator_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Lakeshore temperature channel A (regulator)",
        readpv=f"{pv_root}TempA-r",
        nexus_config=[
            {
                "group_name": "pumping_cart_205",
                "nx_class": "NXcollection",
                "units": "K",
                "suffix": "readback",
                "source_name": f"{pv_root}TempA-r",
                "schema": "f144",
                "topic": "bifrost_sample_env",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
    ),
    sample_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Lakeshore temperature channel B (sample)",
        readpv=f"{pv_root}TempB-r",
        nexus_config=[
            {
                "group_name": "pumping_cart_205",
                "nx_class": "NXcollection",
                "units": "K",
                "suffix": "readback",
                "source_name": f"{pv_root}TempB-r",
                "schema": "f144",
                "topic": "bifrost_sample_env",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
    ),
    lakeshore_temp_c=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Lakeshore temperature channel C",
        readpv=f"{pv_root}TempC-r",
        nexus_config=[
            {
                "group_name": "pumping_cart_205",
                "nx_class": "NXcollection",
                "units": "K",
                "suffix": "readback",
                "source_name": f"{pv_root}TempC-r",
                "schema": "f144",
                "topic": "bifrost_sample_env",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
    ),
    lakeshore_temp_d=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Lakeshore temperature channel D",
        readpv=f"{pv_root}TempD-r",
        nexus_config=[
            {
                "group_name": "pumping_cart_205",
                "nx_class": "NXcollection",
                "units": "K",
                "suffix": "readback",
                "source_name": f"{pv_root}TempD-r",
                "schema": "f144",
                "topic": "bifrost_sample_env",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
    ),
    # ------------------------------------------------------------------
    # Vacuum transducers on the pumping cart
    # ------------------------------------------------------------------
    pressure_sensor_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Vacuum transducer 1 (pumping cart 205)",
        readpv=f"{pv_root}P1-r",
        abslimits=(0, 1100),
        userlimits=(0, 1100),
        nexus_config=[
            {
                "group_name": "pumping_cart_205",
                "nx_class": "NXcollection",
                "units": "hPa",
                "suffix": "readback",
                "source_name": f"{pv_root}P1-r",
                "schema": "f144",
                "topic": "bifrost_sample_env",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
    ),
    pressure_sensor_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Vacuum transducer 2 (pumping cart 205)",
        readpv=f"{pv_root}P2-r",
        abslimits=(0, 1100),
        userlimits=(0, 1100),
        nexus_config=[
            {
                "group_name": "pumping_cart_205",
                "nx_class": "NXcollection",
                "units": "hPa",
                "suffix": "readback",
                "source_name": f"{pv_root}P2-r",
                "schema": "f144",
                "topic": "bifrost_sample_env",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
    ),
    # ------------------------------------------------------------------
    # Nitrogen level and filling control
    # ------------------------------------------------------------------
    ln2_level=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Liquid-nitrogen level",
        readpv=f"{pv_root}LN2-r",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    ln2f_fill_switch=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Start/stop LN2 fill",
        readpv=f"{pv_root}LN2F-Fill-s",
        writepv=f"{pv_root}LN2F-Fill-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    ln2f_auto_switch=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="LN2 auto-fill on/off",
        readpv=f"{pv_root}LN2F-Auto-s",
        writepv=f"{pv_root}LN2F-Auto-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    ln2f_state=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="State of the LN2 filling state machine",
        readpv=f"{pv_root}LN2F-State-r",
    ),
    ln2f_activity=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="LN2 filling in progress",
        readpv=f"{pv_root}LN2F-r",
    ),
    # ------------------------------------------------------------------
    # Flush cycle
    # ------------------------------------------------------------------
    flush_switch=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Start/stop the Flush cycle",
        readpv=f"{pv_root}Flush-s",
        writepv=f"{pv_root}Flush-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    flush_state=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Current state of the Flush state machine",
        readpv=f"{pv_root}Flush-State-r",
    ),
    # ------------------------------------------------------------------
    # Cold valve
    # ------------------------------------------------------------------
    cvalve_position=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cold valve current position",
        readpv=f"{pv_root}CValve-r",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    cvalve_target=device(
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
    p_reg_pressure_setpoint=device(
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
    reg_heater_power=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Regulator heater power (readback)",
        readpv=f"{pv_root}reg-htr-r",
    ),
    reg_heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Regulator heater range",
        readpv=f"{pv_root}reg-htr_range-s",
        writepv=f"{pv_root}reg-htr_range-s",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    reg_heater_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Regulator heater set point",
        readpv=f"{pv_root}reg-setpoint-s",
        writepv=f"{pv_root}reg-setpoint-s",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    # ------------------------------------------------------------------
    # Sample-heater channels
    # ------------------------------------------------------------------
    sample_heater_power=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Sample heater power (readback)",
        readpv=f"{pv_root}sample-htr-r",
    ),
    sample_heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Sample heater range",
        readpv=f"{pv_root}sample-htr_range-s",
        writepv=f"{pv_root}sample-htr_range-s",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    sample_heater_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Sample heater set point",
        readpv=f"{pv_root}sample-setpoint-s",
        writepv=f"{pv_root}sample-setpoint-s",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
)
