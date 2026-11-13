devices = dict(
    ngem_nexus=device(
        "nicos_ess.devices.datasinks.portable_nexus_group.PortableNexusGroup",
        description="Portable nGEM event detector.",
        geometry="ngem",
        group_name="ngem",
        source_name="ngem",
        data_topic="test_detector_portable_ngem",
    ),
)
