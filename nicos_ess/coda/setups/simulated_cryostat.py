"""Simulated sample temperature environment for Coda NeXus tests."""

description = "Simulated cryostat with a logged sample thermometer"
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
    simulated_sample_temperature=device(
        "nicos_ess.coda.devices.simulated_cryostat.SimulatedCryostatParameter",
        description="Simulated sample temperature",
        device="simulated_cryostat",
        parameter="sample",
        unit="K",
        pollinterval=1,
        nexus_config=[
            {
                "nexus_path": "/entry/sample",
                "group_name": "simulated_cryostat",
                "nx_class": "NXenvironment",
                "dataset_type": "nx_log",
                "units": "K",
            },
        ],
    ),
)
