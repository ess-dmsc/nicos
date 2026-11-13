description = "Portable nGEM detector"

# Both use the same just-bin-it service.
excludes = ["just-bin-it"]

INSTRUMENT = "bifrost"
SOURCE_NAME = "ngem"
DATA_TOPIC = f"{INSTRUMENT}_detector_portable_ngem"

devices = dict(
    ngem_nexus=device(
        "nicos_ess.devices.datasinks.portable_nexus_group.PortableNexusGroup",
        description="Portable nGEM event detector.",
        geometry="ngem",
        group_name="ngem",
        source_name=SOURCE_NAME,
        data_topic=DATA_TOPIC,
    ),
    ngem_detector=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItDetector",
        description="The just-bin-it histogrammer for the nGEM",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="",
        event_schema="ev44",
        hist_schema="hs01",
        command_topic=f"{INSTRUMENT}_jbi_commands",
        response_topic=f"{INSTRUMENT}_jbi_responses",
        statustopic=[f"{INSTRUMENT}_jbi_heartbeat"],
        images=["ngem_image", "ngem_tof"],
        timers=["ngem_timer"],
    ),
    ngem_image=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="nGEM image",
        hist_topic=f"{INSTRUMENT}_visualisation",
        data_topic=DATA_TOPIC,
        source=SOURCE_NAME,
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="evts",
        hist_type="2-D DET",
        det_width=128,
        det_height=128,
        det_range=(1, 16384),
        tof_range=(0, 71428571),
    ),
    ngem_tof=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="nGEM time-of-flight spectrum",
        hist_topic=f"{INSTRUMENT}_visualisation",
        data_topic=DATA_TOPIC,
        source=SOURCE_NAME,
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="evts",
        hist_type="1-D TOF",
        det_width=128,
        det_height=128,
        det_range=(1, 16384),
        tof_range=(0, 71428571),
    ),
    ngem_timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer for the nGEM",
        fmtstr="%.2f",
        unit="s",
    ),
)
