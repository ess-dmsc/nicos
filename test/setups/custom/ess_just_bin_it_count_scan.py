# Minimal just-bin-it setup used by command tests.
#
# Two image channels are attached so tests can show the difference between a
# detector-wide timer preset and a preset targeting one specific image channel.
includes = ["ess_count_scan_common"]

devices = dict(
    image_1=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="just-bin-it image 1",
        brokers=["localhost:9092"],
        hist_topic="jbi_hist_1",
        data_topic="jbi_data_1",
        hist_type="1-D TOF",
        num_bins=4,
        rotation=0,
    ),
    image_2=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="just-bin-it image 2",
        brokers=["localhost:9092"],
        hist_topic="jbi_hist_2",
        data_topic="jbi_data_2",
        hist_type="1-D TOF",
        num_bins=4,
        rotation=0,
    ),
    jbi_detector=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItDetector",
        description="The just-bin-it histogrammer",
        brokers=["localhost:9092"],
        event_schema="ev44",
        hist_schema="hs01",
        command_topic="jbi_commands",
        response_topic="jbi_responses",
        ack_timeout=1,
        statustopic=[],
        images=["image_1", "image_2"],
        timers=["timer"],
    ),
)
