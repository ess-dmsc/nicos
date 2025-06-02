description = "The beamlime interface for tbl."

devices = dict(
    monitor1_current=device(
        "nicos_ess.devices.datasources.beamlime.DataChannel",
        description="Sliding time window monitor",
        source_name="monitor1/monitor_data/current",
        type="counter",
    ),
    monitor1_cumulative=device(
        "nicos_ess.devices.datasources.beamlime.DataChannel",
        description="Accumulated monitor",
        source_name="monitor1/monitor_data/cumulative",
        type="counter",
    ),
    beamlime_collector=device(
        "nicos_ess.devices.datasources.beamlime.BeamLimeCollector",
        description="The beamlime detector collector",
        brokers=configdata("config.KAFKA_BROKERS"),
        topic=["tbl_beamlime_data"],
        command_topic="tbl_beamlime_commands",
        others=["monitor1_current", "monitor1_cumulative"],
        schema="da00",
    ),
)
