description = "The livedata interface for dream."

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
    monitor2_current=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Sliding time window monitor",
        type="counter",
    ),
    monitor2_cumulative=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated monitor",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata detector collector",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["dream_livedata_data"],
        status_topics=["dream_livedata_heartbeat"],
        responses_topics=["dream_livedata_responses"],
        commands_topic="dream_livedata_commands",
        others=[
            "monitor1_current",
            "monitor1_cumulative",
            "monitor2_current",
            "monitor2_cumulative"
            ],
    ),
)