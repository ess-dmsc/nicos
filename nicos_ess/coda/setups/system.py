# ruff: noqa: F821

description = "system setup"

group = "lowlevel"

sysconfig = dict(
    cache="localhost",
    instrument="CODA",
    experiment="Exp",
    datasinks=["conssink", "daemonsink", "liveview"],
)

alias_config = {
    "NexusStructure": {
        "NexusStructure_loki": 100,
        "NexusStructure_dream": 99,
        "NexusStructure_bifrost": 98,
        "NexusStructure_nmx": 97,
        "NexusStructure_odin": 96,
        "NexusStructure_tbl": 95,
    },
}

modules = ["nicos.commands.standard", "nicos_ess.commands"]

devices = dict(
    CODA=device(
        "nicos.devices.instrument.Instrument",
        description="instrument object",
        instrument="CODA",
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
        sample="Sample",
        cache_filepath="/opt/nicos-data/cached_proposals.json",
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
    NexusStructure_loki=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nexus-json-templates/loki/loki-dynamic.json",
        instrument_name="loki",
        visibility=(),
    ),
    NexusStructure_dream=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nexus-json-templates/dream/dream-dynamic.json",
        instrument_name="dream",
        visibility=(),
    ),
    NexusStructure_bifrost=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nexus-json-templates/bifrost/bifrost-dynamic.json",
        instrument_name="bifrost",
        visibility=(),
    ),
    NexusStructure_nmx=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nexus-json-templates/nmx/nmx-dynamic.json",
        instrument_name="nmx",
        visibility=(),
    ),
    NexusStructure_odin=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nexus-json-templates/odin/odin-dynamic.json",
        instrument_name="odin",
        visibility=(),
    ),
    NexusStructure_tbl=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nexus-json-templates/tbl/tbl-mb-dynamic.json",
        instrument_name="tbl",
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
        statustopic=["coda_filewriter", "ess_filewriter_status"],
        unit="",
    ),
    FileWriterControl=device(
        "nicos_ess.devices.datasinks.file_writer.FileWriterControlSink",
        description="Control for the file-writer",
        brokers=configdata("config.KAFKA_BROKERS"),
        pool_topic="ess_filewriter_pool",
        instrument_topic="coda_filewriter",
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
