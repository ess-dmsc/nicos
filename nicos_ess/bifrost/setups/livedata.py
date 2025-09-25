description = "The livedata."

devices = dict(
    detector_sliding=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A just-bin-it image channel",
        source_name="unified_detector:unified_detector/sliding",
        type="counter",
    ),
    detector_cumulative=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A just-bin-it image channel",
        source_name="unified_detector:unified_detector/cumulative",
        type="counter",
    ),
    detector_roi=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A just-bin-it image channel",
        source_name="unified_detector:unified_detector/roi",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The just-bin-it histogrammer",
        brokers=["10.100.4.15:8093", "10.100.4.17:8093", "10.100.5.29:8093"],
        topic=["bifrost_livedata_data"],
        command_topic="bifrost_livedata_commands",
        others=["detector_sliding", "detector_cumulative", "detector_roi"],
        schema="da00",
    ),
)
