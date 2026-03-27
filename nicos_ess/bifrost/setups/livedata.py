description = "The livedata interface for bifrost."

devices = dict(
    detector_sliding=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Configurable BIFROST livedata channel",
        type="counter",
    ),
    detector_cumulative=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Configurable BIFROST livedata channel",
        type="counter",
    ),
    detector_roi=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Configurable BIFROST livedata channel",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata detector collector",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["bifrost_livedata_data"],
        commands_topic="bifrost_livedata_commands",
        counters=["detector_sliding", "detector_cumulative", "detector_roi"],
    ),
)
