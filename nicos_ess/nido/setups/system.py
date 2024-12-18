# ruff: noqa: F821
description = "system setup"

group = "lowlevel"

sysconfig = dict(
    cache="localhost",
    instrument="NIDO",
    experiment="Exp",
    datasinks=["conssink", "daemonsink", "liveview"],
)


modules = ["nicos.commands.standard", "nicos_ess.commands"]

alias_config = {
    "NexusStructure": {
        "NexusStructure_Basic": 50,
    },
}

KAFKA_BROKERS = ["10.102.80.32:8093"]

devices = dict(
    NIDO=device(
        "nicos.devices.instrument.Instrument",
        description="instrument object",
        instrument="NIDO",
        responsible="M. Clarke <matt.clarke@ess.eu>",
    ),
    Sample=device(
        "nicos_ess.devices.sample.EssSample",
        description="The currently used sample",
    ),
    Exp=device(
        "nicos_ess.devices.experiment.EssExperiment",
        description="experiment object",
        dataroot="/opt/nicos-data",
        fixed_proposal_path="",
        sample="Sample",
        cache_filepath="/opt/nicos-data/cached_proposals.json",
    ),
    pnp_listener=device(
        "nicos_ess.devices.pnp_listener.UDPHeartbeatsManager",
        description="Listens for PnP heartbeats",
        port=24601,
    ),
    conssink=device(
        "nicos_ess.devices.datasinks.console_scan_sink.ConsoleScanSink",
    ),
    daemonsink=device(
        "nicos.devices.datasinks.DaemonSink",
    ),
    liveview=device(
        "nicos.devices.datasinks.LiveViewSink",
    ),
    NexusStructure_Basic=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nicos_ess/nido/nexus/nido_nexus.json",
        visibility=(),
    ),
    NexusStructure=device(
        "nicos.devices.generic.DeviceAlias",
        devclass="nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
    ),
    FileWriterStatus=device(
        "nicos_ess.devices.datasinks.file_writer.FileWriterStatus",
        description="Status of the file-writer",
        brokers=configdata("config.KAFKA_BROKERS"),
        statustopic=["nido_filewriter"],
        unit="",
    ),
    FileWriterControl=device(
        "nicos_ess.devices.datasinks.file_writer.FileWriterControlSink",
        description="Control for the file-writer",
        brokers=configdata("config.KAFKA_BROKERS"),
        pool_topic="ess_filewriter_pool",
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
