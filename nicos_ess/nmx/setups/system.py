# ruff: noqa: F821
description = "system setup"

group = "lowlevel"

sysconfig = dict(
    cache="localhost",
    instrument="NMX",
    experiment="Exp",
    datasinks=["conssink", "liveview", "daemonsink", "scanlog"],
)

modules = ["nicos.commands.standard", "nicos_ess.commands"]

devices = dict(
    NMX=device(
        "nicos.devices.instrument.Instrument",
        description="instrument object",
        instrument="NMX",
        responsible="Esko Oksanen <esko.oksanen@ess.eu>",
        website="https://europeanspallationsource.se/instruments/nmx",
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
        "nicos_ess.devices.datasinks.live_view.ReducedLiveViewSink",
    ),
    scanlog=device(
        "nicos_ess.devices.datasinks.scan_log.ScanLogSink",
        brokers=configdata("config.KAFKA_BROKERS"),
        topic="nmx_nicos_devices",
    ),
    KafkaForwarder=device(
        "nicos_ess.devices.forwarder.EpicsKafkaForwarder",
        description="Monitors the status of the Forwarder",
        statustopic=["nmx_forwarder_dynamic_status"],
        config_topic="nmx_forwarder_dynamic_config",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
    NexusStructure_Basic=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nexus-json-templates/nmx/nmx-dynamic.json",
        instrument_name="nmx",
        visibility=(),
    ),
    NexusStructure=device(
        "nicos.devices.generic.DeviceAlias",
        alias="NexusStructure_Basic",
        devclass="nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
    ),
    FileWriter=device(
        "nicos_ess.devices.datasinks.file_writer.FileWriter",
        description="Starts and stops file writing jobs",
        brokers=configdata("config.KAFKA_BROKERS"),
        statustopic=["nmx_filewriter", "ess_filewriter_status"],
        pool_topic="ess_filewriter_pool",
        instrument_topic="nmx_filewriter",
        nexus="NexusStructure",
        unit="",
    ),
)
