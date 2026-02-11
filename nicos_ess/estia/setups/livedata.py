description = "The livedata."

devices = dict(
    channel_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="An estia livedata channel",
        type="counter",
    ),
    det=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata histogrammer",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["livedata_data"],
        command_topic="livedata_commands",
        status_topics=["livedata_status"],
        others=["channel_1"],
    ),
)
