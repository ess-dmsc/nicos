description = "The livedata interface for tbl."

devices = dict(
    monitor1_current=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Sliding time window monitor",
        source_name="monitor1/monitor_data/current",
        type="counter",
    ),
    monitor1_cumulative=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated monitor",
        source_name="monitor1/monitor_data/cumulative",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata detector collector",
        brokers=configdata("config.KAFKA_BROKERS"),
        topic=["tbl_livedata_data"],
        command_topic="tbl_livedata_commands",
        others=["monitor1_current", "monitor1_cumulative"],
        schema="da00",
    ),
)
