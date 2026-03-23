includes = ["axis"]

devices = dict(
    livedata_primary=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        selector="",
        type="counter",
    ),
    livedata_secondary=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        selector="",
        type="counter",
    ),
    livedata_roi=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        selector="",
        type="counter",
    ),
    livedata_detector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        brokers=["localhost:9092"],
        data_topics=["livedata"],
        status_topics=[],
        responses_topics=[],
        commands_topic="",
        counters=["livedata_primary", "livedata_secondary", "livedata_roi"],
    ),
)
