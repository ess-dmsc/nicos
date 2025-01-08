# ruff: noqa: F821
description = "system setup"

group = "lowlevel"

sysconfig = dict(
    cache="localhost",
    instrument="BIFROST",
    experiment="Exp",
    datasinks=["conssink", "daemonsink", "liveview"],
)

modules = ["nicos.commands.standard", "nicos_ess.commands"]

devices = dict(
    BIFROST=device(
        "nicos.devices.instrument.Instrument",
        description="instrument object",
        facility="European Spallation Source (ERIC)",
        instrument="BIFROST",
        responsible="Rasmus Toft-Petersen <rasmus.toft-petersen@ess.eu>",
        website="https://europeanspallationsource.se/instruments/bifrost",
    ),
    Sample=device(
        "nicos_ess.devices.sample.EssSample",
        description="The currently used sample",
    ),
    Exp=device(
        "nicos_ess.devices.experiment.EssExperiment",
        description="experiment object",
        dataroot="/opt/nicos-data",
        sample="Sample",
        cache_filepath="/opt/nicos-data/cached_proposals.json",
    ),
    pnp_listener=device(
        "nicos_ess.devices.pnp_listener.UDPHeartbeatsManager",
        description="Listens for PnP heartbeats",
        port=24601,
    ),
    conssink=device("nicos_ess.devices.datasinks.console_scan_sink.ConsoleScanSink"),
    daemonsink=device("nicos.devices.datasinks.DaemonSink"),
    liveview=device("nicos.devices.datasinks.LiveViewSink"),
    KafkaForwarderStatus=device(
        "nicos_ess.devices.forwarder.EpicsKafkaForwarder",
        description="Monitors the status of the Forwarder",
        statustopic=["bifrost_forwarder_dynamic_status"],
        config_topic="bifrost_forwarder_dynamic_config",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
    NexusStructure_Basic=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nexus-json-templates/bifrost/bifrost-dynamic.json",
        instrument_name="bifrost",
        visibility=(),
    ),
    NexusStructure=device(
        "nicos.devices.generic.DeviceAlias",
        alias="NexusStructure_Basic",
        devclass="nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
    ),
    FileWriterStatus=device(
        "nicos_ess.devices.datasinks.file_writer.FileWriterStatus",
        description="Status of the file-writer",
        brokers=configdata("config.KAFKA_BROKERS"),
        statustopic=["bifrost_filewriter"],
        unit="",
    ),
    FileWriterControl=device(
        "nicos_ess.devices.datasinks.file_writer.FileWriterControlSink",
        description="Control for the file-writer",
        brokers=configdata("config.KAFKA_BROKERS"),
        pool_topic="ess_filewriter_pool",
        instrument_topic="bifrost_filewriter",
        status="FileWriterStatus",
        nexus="NexusStructure",
        use_instrument_directory=True,
    ),
    SciChat=device(
        "nicos_ess.devices.scichat.ScichatBot",
        description="Sends messages to SciChat",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
)
