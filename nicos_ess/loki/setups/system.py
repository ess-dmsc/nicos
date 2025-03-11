# ruff: noqa: F821
description = "system setup"

group = "lowlevel"

sysconfig = dict(
    cache="localhost",
    instrument="LoKI",
    experiment="Exp",
    datasinks=["conssink", "liveview", "daemonsink"],
)

modules = ["nicos.commands.standard", "nicos_ess.commands"]

devices = dict(
    LoKI=device(
        "nicos.devices.instrument.Instrument",
        description="instrument object",
        instrument="LoKI",
        responsible="J. Houston <judith.houston@ess.eu>",
        website="https://europeanspallationsource.se/instruments/loki",
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
    conssink=device("nicos_ess.devices.datasinks.console_scan_sink.ConsoleScanSink"),
    daemonsink=device(
        "nicos.devices.datasinks.DaemonSink",
    ),
    liveview=device(
        "nicos.devices.datasinks.LiveViewSink",
    ),
    KafkaForwarderStatus=device(
        "nicos_ess.devices.forwarder.EpicsKafkaForwarder",
        description="Monitors the status of the Forwarder",
        statustopic=["loki_forwarder_dynamic_status"],
        config_topic="loki_forwarder_dynamic_config",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
    NexusStructure_Basic=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nexus-json-templates/loki/loki-dynamic.json",
        instrument_name="loki",
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
        statustopic=["loki_filewriter", "ess_filewriter_status"],
        unit="",
    ),
    FileWriterControl=device(
        "nicos_ess.devices.datasinks.file_writer.FileWriterControlSink",
        description="Control for the file-writer",
        brokers=configdata("config.KAFKA_BROKERS"),
        pool_topic="ess_filewriter_pool",
        instrument_topic="loki_filewriter",
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
