"""Simulated sample temperature environment for Coda NeXus tests."""

description = "Simulated cryostat with logged temperatures and controller metadata"
group = "optional"

# NeXus groups as (nexus_path, group_name, nx_class).
sample = ("/entry", "sample", "NXsample")
environment = ("/entry/sample", "temperature_env", "NXenvironment")
heater = ("/entry/sample/temperature_env", "heater", "NXactuator")
heater_path = "/entry/sample/temperature_env/heater"
pid = (heater_path, "pid_controller", "NXpid_controller")
pv_sensor = (heater_path + "/pid_controller", "pv_sensor", "NXsensor")


def nexus_config(nexus_group, name, dataset_type, **kwargs):
    nexus_path, group_name, nx_class = nexus_group
    return dict(
        nexus_path=nexus_path,
        group_name=group_name,
        nx_class=nx_class,
        name=name,
        dataset_type=dataset_type,
        **kwargs,
    )


devices = dict(
    simulated_cryostat=device(
        "nicos_ess.coda.devices.simulated_cryostat.SimulatedCryostat",
        description="Simulated cryostat temperature controller",
        unit="K",
        abslimits=(2, 350),
        ramp=6,
        jitter=0,
        precision=0.1,
        window=30,
        nexus_config=[
            nexus_config(
                environment, "name", "static_value", value="simulated_cryostat"
            ),
            nexus_config(environment, "type", "static_value", value="cryostat"),
            nexus_config(
                heater, "physical_quantity", "static_value", value="temperature"
            ),
            nexus_config(
                heater, "actuation_target", "static_value", value="/entry/sample"
            ),
            nexus_config(pid, "control_action", "static_value", value="direct"),
            nexus_config(pv_sensor, "measurement", "static_value", value="temperature"),
        ],
    ),
)

# Each parameter is written as a field read at the start of the run, as a log
# of its values during the run, or both. The NICOS collector does not forward
# string values, so the mode has no log.
for name, parameter, unit, nexus_group, field_name, log_name in [
    ("sample_temperature", "sample", "K", sample, None, "temperature"),
    ("regulator_temperature", "regulation", "K", pv_sensor, None, "value_log"),
    ("heater_power", "heaterpower", "W", heater, "output_power", "output_power_log"),
    ("heater_output", "heater", "percent", heater, "output_level", "output_level_log"),
    ("max_heater_power", "maxpower", "W", heater, "max_power", "max_power_log"),
    ("setpoint", "setpoint", "K", pid, "setpoint", "setpoint_log"),
    ("target", "target", "K", pid, "target", "target_log"),
    ("ramp", "ramp", "K/min", pid, "ramp", "ramp_log"),
    # LakeShore-style settings, not the K_p, K_i and K_d gains of
    # NXpid_controller: p = 10*K_p, i = 500/T_i, d = 2*T_d.
    ("pid_p", "p", "percent/K", pid, "p_setting", "p_setting_log"),
    ("pid_i", "i", "1/s", pid, "i_setting", "i_setting_log"),
    ("pid_d", "d", "s", pid, "d_setting", "d_setting_log"),
    ("mode", "mode", "", pid, "mode", None),
]:
    nexus_configs = []
    if field_name:
        nexus_configs.append(
            nexus_config(nexus_group, field_name, "static_read", units=unit)
        )
    if log_name:
        nexus_configs.append(nexus_config(nexus_group, log_name, "nx_log", units=unit))

    devices["simulated_" + name] = device(
        "nicos_ess.coda.devices.simulated_cryostat.SimulatedCryostatParameter",
        description="Simulated cryostat " + name.replace("_", " "),
        device="simulated_cryostat",
        parameter=parameter,
        unit=unit,
        visibility=("metadata",),
        pollinterval=1,
        nexus_config=nexus_configs,
    )
