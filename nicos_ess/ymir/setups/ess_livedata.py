description = "ESS livedata"

devices = dict(
    channel_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["dream_livedata_data"],
        status_topics=["dream_livedata_heartbeat"],
        responses_topics=["dream_livedata_responses"],
        commands_topic=["dream_livedata_commands"],
        others=["channel_1"],
    ),
)
