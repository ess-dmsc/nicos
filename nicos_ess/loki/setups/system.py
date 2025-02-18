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
    FileWriter=device(
        "nicos_ess.devices.datasinks.file_writer.Filewriter",
        description="Device that controls the filewriter",
        brokers=configdata("config.KAFKA_BROKERS"),
        pool_topic="ess_filewriter_pool",
        instrument_topic="loki_filewriter",
        statustopic=["loki_filewriter", "ess_filewriter_status"],
        timeoutinterval=5,
        stoptimeout=5,
        nexus="NexusStructure",
    ),
    SciChat=device(
        "nicos_ess.devices.scichat.ScichatBot",
        description="Sends messages to SciChat",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
)
