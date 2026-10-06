"""Simulated sample temperature environment for Coda NeXus tests."""

description = "Simulated cryostat with logged temperatures and controller metadata"
group = "optional"

devices = dict(
    simulated_cryostat=device(
        "nicos.devices.generic.VirtualRealTemperature",
        description="Simulated cryostat temperature controller",
        unit="K",
        abslimits=(2, 350),
        ramp=6,
        jitter=0,
        precision=0.1,
        window=30,
    ),
)

# Each numeric parameter gets its own scalar NICOS stream. Capture the string
# mode once when building the NeXus structure, using static_read.
for name, parameter, unit in [
    ("sample_temperature", "sample", "K"),
    ("regulator_temperature", "regulation", "K"),
    ("setpoint", "setpoint", "K"),
    ("target", "target", "K"),
    ("ramp", "ramp", "K/min"),
    ("pid_p", "p", "percent/K"),
    ("pid_i", "i", "percent/(K*s)"),
    ("pid_d", "d", "percent*s/K"),
    ("heater_output", "heater", "percent"),
    ("heater_power", "heaterpower", "W"),
    ("max_heater_power", "maxpower", "W"),
    ("loop_delay", "loopdelay", "s"),
    ("speedup", "speedup", "1"),
    ("jitter", "jitter", "K"),
    ("precision", "precision", "K"),
    ("window", "window", "s"),
    ("mode", "mode", ""),
]:
    devices["simulated_" + name] = device(
        "nicos_ess.coda.devices.simulated_cryostat.SimulatedCryostatParameter",
        description="Simulated cryostat " + name.replace("_", " "),
        device="simulated_cryostat",
        parameter=parameter,
        unit=unit,
        visibility=("metadata",),
        pollinterval=1,
        nexus_config=[
            dict(
                nexus_path="/entry/sample",
                group_name="simulated_cryostat",
                nx_class="NXenvironment",
                dataset_type="static_read" if parameter == "mode" else "nx_log",
                units=unit,
            ),
        ],
    )
