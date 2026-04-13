description = "The livedata interface for tbl."

devices = dict(
    monitor1_current=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Sliding time window monitor",
        type="counter",
    ),
    monitor1_cumulative=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated monitor",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata detector collector",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["tbl_livedata_data"],
        commands_topic="tbl_livedata_commands",
        others=["monitor1_current", "monitor1_cumulative"],
    ),
)
