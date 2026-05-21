description = "The livedata interface for tbl."

devices = dict(
    channel_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A TBL livedata channel",
        type="counter",
    ),
    channel_2=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A TBL livedata channel",
        type="counter",
    ),
    channel_3=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A TBL livedata channel",
        type="counter",
    ),
    channel_4=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A TBL livedata channel",
        type="counter",
    ),
    channel_5=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A TBL livedata channel",
        type="counter",
    ),
    channel_6=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A TBL livedata channel",
        type="counter",
    ),
    channel_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata histogrammer",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["tbl_livedata_data"],
        commands_topic="tbl_livedata_commands",
        status_topics=["tbl_livedata_heartbeat"],
        others=[
            "channel_1",
            "channel_2",
            "channel_3",
            "channel_4",
            "channel_5",
            "channel_6",
        ],
    ),
)
