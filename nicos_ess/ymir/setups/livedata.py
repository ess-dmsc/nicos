description = "ESSlivedata setup"

devices = dict(
    channel_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A livedata channel",
        type="counter",
    ),
    channel_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata collector",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["bifrost_livedata_data"],
        commands_topic="bifrost_livedata_commands",
        status_topics=["bifrost_livedata_heartbeat"],
        others=["channel_1"],
        service_name="unified_detector",
    ),
)
