includes = ["axis"]

devices = dict(
    livedata_channel=device(
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
        others=["livedata_channel"],
    ),
)
