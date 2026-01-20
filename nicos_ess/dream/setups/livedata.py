description = "The livedata interface for dream."

devices = dict(
    channel_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Sliding time window monitor",
        type="counter",
    ),
    channel_2=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated monitor",
        type="counter",
    ),
    channel_3=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Sliding time window monitor",
        type="counter",
    ),
    channel_4=device(
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
            "channel_1",
            "channel_2",
            "channel_3",
            "channel_4"
            ],
    ),
)