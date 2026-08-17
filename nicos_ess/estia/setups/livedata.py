description = "The livedata."

devices = dict(
    channel_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="An estia livedata channel",
        device_name="cbm1_counts_total",
        workflow_id="estia/monitor_histogram/1",
        type="counter",
    ),
    channel_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata histogrammer",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["estia_livedata_data"],
        commands_topic="estia_livedata_commands",
        status_topics=["estia_livedata_heartbeat"],
        others=["channel_1"],
    ),
)
