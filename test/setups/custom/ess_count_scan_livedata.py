includes = ["axis"]

devices = dict(
    livedata_timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        fmtstr="%.2f",
        unit="s",
        update_interval=0.01,
    ),
    livedata_current=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        selector="dummy/detector_data/panel_0_tof/1@panel_0#job-1/current",
        type="counter",
    ),
    livedata_cumulative=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        selector="dummy/detector_data/panel_0_tof/1@panel_0#job-1/cumulative",
        type="counter",
    ),
    livedata_detector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        brokers=["localhost:9092"],
        data_topics=["livedata"],
        status_topics=[],
        responses_topics=[],
        commands_topic="",
        timers=["livedata_timer"],
        counters=["livedata_current", "livedata_cumulative"],
    ),
)
