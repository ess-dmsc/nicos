includes = ["axis"]

devices = dict(
    jbi_timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        fmtstr="%.2f",
        unit="s",
        update_interval=0.01,
    ),
    pulse_counter=device(
        "nicos_ess.devices.epics.pulse_counter.PulseCounter",
        readpv="SIM:PULSE",
        fmtstr="%d",
    ),
    jbi_image_fast=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        brokers=["localhost:9092"],
        hist_topic="jbi_hist_fast",
        data_topic="jbi_data_fast",
        hist_type="1-D TOF",
        num_bins=5,
    ),
    jbi_image_slow=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        brokers=["localhost:9092"],
        hist_topic="jbi_hist_slow",
        data_topic="jbi_data_slow",
        hist_type="1-D TOF",
        num_bins=5,
    ),
    jbi_detector=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItDetector",
        brokers=["localhost:9092"],
        command_topic="jbi_command",
        response_topic="jbi_response",
        statustopic=[],
        images=["jbi_image_fast", "jbi_image_slow"],
        timers=["jbi_timer"],
        counters=["pulse_counter"],
        event_schema="ev44",
        hist_schema="hs01",
        liveinterval=1,
    ),
)
