# ruff: noqa: F821
import os

description = "system setup for NICOS smoke integration"

group = "lowlevel"

# The runner injects a temp root; the fallback keeps manual imports out of git.
_runtime_root = os.environ.get("NICOS_SMOKE_RUNTIME_ROOT", "/tmp/nicos-smoke-manual")

sysconfig = dict(
    cache=configdata("config.CACHE_HOST"),
    instrument="SMOKE",
    experiment="Exp",
    datasinks=["conssink", "daemonsink", "liveview"],
)

modules = ["nicos.commands.standard", "nicos_ess.commands"]

devices = dict(
    SMOKE=device(
        "nicos.devices.instrument.Instrument",
        description="smoke instrument object",
        instrument="SMOKE",
        responsible="nicos.integration@example.org",
    ),
    Sample=device(
        "nicos_ess.devices.sample.EssSample",
        description="The currently used sample",
    ),
    Exp=device(
        "nicos_ess.devices.experiment.EssExperiment",
        description="experiment object",
        dataroot=os.path.join(_runtime_root, "data"),
        sample="Sample",
        cache_filepath=os.path.join(_runtime_root, "cached_proposals.json"),
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
    KafkaForwarder=device(
        "nicos_ess.devices.forwarder.EpicsKafkaForwarder",
        description="Monitors and configures the Forwarder",
        statustopic=configdata("config.FORWARDER_STATUS_TOPIC"),
        config_topic=configdata("config.FORWARDER_CONFIG_TOPIC"),
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
    NexusStructure_Basic=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        # Keep smoke independent of site/instrument NeXus configs.
        nexus_config_path="integration_test/smoke/nexus/smoke_nexus.json",
        instrument_name="",
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
        statustopic=configdata("config.FILEWRITER_STATUS_TOPICS"),
        unit="",
    ),
    FileWriterControl=device(
        "nicos_ess.devices.datasinks.file_writer.FileWriterControlSink",
        description="Control for the file-writer",
        brokers=configdata("config.KAFKA_BROKERS"),
        pool_topic=configdata("config.FILEWRITER_POOL_TOPIC"),
        instrument_topic=configdata("config.FILEWRITER_INSTRUMENT_TOPIC"),
        status="FileWriterStatus",
        nexus="NexusStructure",
        use_instrument_directory=True,
    ),
    SciChat=device(
        "nicos_ess.devices.scichat.ScichatBot",
        description="Sends messages to SciChat",
        brokers=configdata("config.KAFKA_BROKERS"),
        scichat_topic=configdata("config.SCICHAT_TOPIC"),
    ),
)
