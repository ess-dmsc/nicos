description = "The livedata."

devices = dict(
    detector_sliding=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A livedata channel",
        selector="",
        type="counter",
    ),
    detector_cumulative=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A livedata channel",
        selector="",
        type="counter",
    ),
    detector_roi=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A livedata channel",
        selector="",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata collector",
        brokers=["10.100.4.15:8093", "10.100.4.17:8093", "10.100.5.29:8093"],
        data_topics=["bifrost_livedata_data"],
        commands_topic="bifrost_livedata_commands",
        counters=["detector_sliding", "detector_cumulative", "detector_roi"],
    ),
)
