includes = ["axis"]

devices = dict(
    jbi_image_fast=device(
        "nicos_ess.devices.virtual.just_bin_it.JustBinItImage",
        brokers=["localhost:9092"],
        hist_topic="sim_jbi_hist_fast",
        data_topic="sim_jbi_data_fast",
        hist_type="1-D TOF",
        num_bins=8,
    ),
    jbi_image_slow=device(
        "nicos_ess.devices.virtual.just_bin_it.JustBinItImage",
        brokers=["localhost:9092"],
        hist_topic="sim_jbi_hist_slow",
        data_topic="sim_jbi_data_slow",
        hist_type="1-D TOF",
        num_bins=8,
    ),
    jbi_detector=device(
        "nicos_ess.devices.virtual.just_bin_it.JustBinItDetector",
        brokers=["localhost:9092"],
        command_topic="sim_jbi_command",
        response_topic="sim_jbi_response",
        statustopic=[],
        images=["jbi_image_fast", "jbi_image_slow"],
        event_schema="ev44",
        hist_schema="hs01",
        liveinterval=0.5,
    ),
)
