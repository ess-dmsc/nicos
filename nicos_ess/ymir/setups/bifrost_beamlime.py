description = "The beamlime."

devices = dict(
    detector_sliding=device(
        "nicos_ess.devices.datasources.beamlime.DataChannel",
        description="A just-bin-it image channel",
        source_name="unified_detector:sliding",
        type="counter",
    ),
    detector_cumulative=device(
        "nicos_ess.devices.datasources.beamlime.DataChannel",
        description="A just-bin-it image channel",
        source_name="unified_detector:cumulative",
        type="counter",
    ),
    detector_roi=device(
        "nicos_ess.devices.datasources.beamlime.DataChannel",
        description="A just-bin-it image channel",
        source_name="unified_detector:roi",
        type="counter",
    ),
    beamlime_collector=device(
        "nicos_ess.devices.datasources.beamlime.BeamLimeCollector",
        description="The just-bin-it histogrammer",
        brokers=["localhost:9092"],
        topic=["bifrost_beamlime_data"],
        command_topic="bifrost_beamlime_data",
        others=["detector_sliding", "detector_cumulative", "detector_roi"],
        schema="da00",
    ),
)
