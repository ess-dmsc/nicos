description = "system setup"

group = "lowlevel"

sysconfig = dict(
    cache="localhost",
    instrument="FREIA",
    experiment="Exp",
    datasinks=["conssink", "daemonsink"],
)

modules = ["nicos.commands.standard", "nicos_ess.commands"]

devices = dict(
    FREIA=device(
        "nicos.devices.instrument.Instrument",
        description="instrument object",
        instrument="FREIA",
        responsible="S. Body <some.body@ess.eu>",
    ),
    Sample=device(
        "nicos.devices.sample.Sample",
        description="The currently used sample",
    ),
    Exp=device(
        "nicos_ess.devices.experiment.EssExperiment",
        description="experiment object",
        dataroot="/opt/nicos-data",
        sample="Sample",
        cache_filepath="/opt/nicos-data/cached_proposals.json",
    ),
    filesink=device(
        "nicos.devices.datasinks.AsciiScanfileSink",
    ),
    conssink=device(
        "nicos.devices.datasinks.ConsoleScanSink",
    ),
    daemonsink=device(
        "nicos.devices.datasinks.DaemonSink",
    ),
    Space=device(
        "nicos.devices.generic.FreeSpace",
        description="The amount of free space for storing data",
        path=None,
        minfree=5,
    ),
    KafkaForwarderStatus=device(
        "nicos_ess.devices.forwarder.EpicsKafkaForwarder",
        description="Monitors the status of the Forwarder",
        statustopic=["freia_forwarder_dynamic_status"],
        config_topic="freia_forwarder_dynamic_config",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
    NexusStructure=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nicos_ess/freia/nexus/nexus_config.json",
        instrument_name="freia",
        visibility=(),
    ),
    FileWriterStatus=device(
        "nicos_ess.devices.datasinks.file_writer.FileWriterStatus",
        description="Status of the file-writer",
        brokers=configdata("config.KAFKA_BROKERS"),
        statustopic=["freia_filewriter", "ess_filewriter_status"],
        unit="",
    ),
    FileWriterControl=device(
        "nicos_ess.devices.datasinks.file_writer.FileWriterControlSink",
        description="Control for the file-writer",
        brokers=configdata("config.KAFKA_BROKERS"),
        pool_topic="ess_filewriter_pool",
        instrument_topic="freia_filewriter",
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
