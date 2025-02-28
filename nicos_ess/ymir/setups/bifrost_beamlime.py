description = "The beamlime."

devices = dict(
    hist_1d_source=device(
        "nicos_ess.devices.datasources.beamlime.DataChannel",
        description="A just-bin-it image channel",
        source_name="hist_1d_source",
        type="counter",
    ),
    hist_2d_source=device(
        "nicos_ess.devices.datasources.beamlime.DataChannel",
        description="A just-bin-it image channel",
        source_name="hist_2d_source",
        type="counter",
    ),
    beamlime_collector=device(
        "nicos_ess.devices.datasources.beamlime.BeamLimeCollector",
        description="The just-bin-it histogrammer",
        brokers=["localhost:9092"],
        topic=["bifrost_beamlime_data"],
        command_topic="bifrost_beamlime_data",
        others=["hist_1d_source", "hist_2d_source"],
        schema="da00",
    ),
)
