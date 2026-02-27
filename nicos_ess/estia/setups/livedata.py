description = "The livedata."

devices = dict(
    channel_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="An estia livedata channel",
        type="counter",
    ),
    channel_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata histogrammer",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["estia_livedata_data"],
        command_topic="estia_livedata_commands",
        status_topics=["estia_livedata_status"],
        others=["channel_1"],
    ),
)
