description = "The livedata interface for dream."

devices = dict(
    channel_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 1",
        type="counter",
    ),
    channel_2=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 2",
        type="counter",
    ),
    channel_3=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 3",
        type="counter",
    ),
    channel_4=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 4",
        type="counter",
    ),
    channel_5=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 5",
        type="counter",
    ),
    channel_6=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 6",
        type="counter",
    ),
    channel_7=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 7",
        type="counter",
    ),
    channel_8=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 8",
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
            "channel_4",
            "channel_5",
            "channel_6",
            "channel_7",
            "channel_8",
            ],
    ),
)