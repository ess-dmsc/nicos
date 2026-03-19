includes = ["axis"]

devices = dict(
    timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        fmtstr="%.2f",
        unit="s",
    ),
    jbi_image=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        brokers=["localhost:9092"],
        hist_topic="jbi_hist",
        data_topic="jbi_data",
        hist_type="1-D TOF",
        num_bins=5,
    ),
    jbi_detector=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItDetector",
        brokers=["localhost:9092"],
        command_topic="jbi_command",
        response_topic="jbi_response",
        statustopic=[],
        images=["jbi_image"],
        timers=["timer"],
        event_schema="ev44",
        hist_schema="hs01",
        liveinterval=1,
    ),
)
