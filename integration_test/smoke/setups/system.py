# ruff: noqa: F821

description = "system setup for full-stack smoke integration"

group = "lowlevel"

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
        dataroot="integration_test/runtime/data",
        sample="Sample",
        cache_filepath="integration_test/runtime/cached_proposals.json",
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
        nexus_config_path="nicos_ess/ymir/nexus/ymir_nexus.json",
        instrument_name="ymir",
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
    SmokeReadable=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsReadable",
        description="Smoke EPICS readable",
        readpv="TEST:SMOKE:READ.RBV",
        monitor=True,
        pva=True,
    ),
    SmokeMoveable=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsAnalogMoveable",
        description="Smoke EPICS analog moveable",
        readpv="TEST:SMOKE:MOVE.RBV",
        writepv="TEST:SMOKE:MOVE.VAL",
        monitor=True,
        pva=True,
        unit="Hz",
        precision=0.01,
    ),
)
