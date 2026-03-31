includes = ["axis"]

devices = dict(
    livedata_timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        fmtstr="%.2f",
        unit="s",
        update_interval=0.01,
    ),
    livedata_current=device(
        "nicos_ess.devices.virtual.livedata.DataChannel",
        selector="dummy/detector_data/panel_0_tof/1@panel_0/current",
        type="counter",
    ),
    livedata_cumulative=device(
        "nicos_ess.devices.virtual.livedata.DataChannel",
        selector="dummy/detector_data/panel_0_tof/1@panel_0/cumulative",
        type="counter",
    ),
    livedata_detector=device(
        "nicos_ess.devices.virtual.livedata.LiveDataCollector",
        brokers=["localhost:9092"],
        data_topics=["sim_livedata_data"],
        status_topics=["sim_livedata_status"],
        responses_topics=["sim_livedata_responses"],
        commands_topic="sim_livedata_commands",
        timers=["livedata_timer"],
        counters=["livedata_current", "livedata_cumulative"],
    ),
)
