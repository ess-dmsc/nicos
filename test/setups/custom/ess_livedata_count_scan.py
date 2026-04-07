includes = ["stdsystem"]

devices = dict(
    axis=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-10, 10),
        curvalue=0,
        unit="deg",
        fmtstr="%.2f",
    ),
    timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer",
        unit="s",
        fmtstr="%.2f",
        update_interval=0.01,
    ),
    channel_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 1",
        selector="test/data_reduction/monitor_data/1@monitor/current",
        type="counter",
    ),
    channel_2=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 2",
        selector="test/data_reduction/monitor_data/1@monitor/cumulative",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata detector collector",
        brokers=["localhost:9092"],
        data_topics=["livedata_data"],
        commands_topic="livedata_commands",
        others=["channel_1", "channel_2"],
        timers=["timer"],
    ),
)
