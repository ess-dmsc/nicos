# ruff: noqa: F821
description = "system setup"

group = "lowlevel"

sysconfig = dict(
    cache="localhost",
    instrument="YMIR",
    experiment="Exp",
    datasinks=["conssink", "daemonsink", "liveview"],
)

alias_config = {
    "NexusStructure": {
        "NexusStructure_Basic": 101,
        "NexusStructure_loki": 100,
        "NexusStructure_dream": 99,
        "NexusStructure_bifrost": 98,
        "NexusStructure_nmx": 97,
        "NexusStructure_odin": 96,
        "NexusStructure_tbl": 95,
        "NexusStructure_estia": 94,
    },
}
modules = ["nicos.commands.standard", "nicos_ess.commands"]

devices = dict(
    YMIR=device(
        "nicos.devices.instrument.Instrument",
        description="instrument object",
        instrument="YMIR",
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
    KafkaForwarder=device(
        "nicos_ess.devices.forwarder.EpicsKafkaForwarder",
        description="Monitors and configures the Forwarder",
        statustopic=["ymir_forwarder_dynamic_status"],
        config_topic="ymir_forwarder_dynamic_config",
        brokers=configdata("config.KAFKA_BROKERS"),
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
        nexus_config_path="nexus-json-templates/tbl/tbl-dynamic.json",
        instrument_name="tbl",
        visibility=(),
    ),
    NexusStructure_estia=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nexus-json-templates/estia/estia-dynamic.json",
        instrument_name="estia",
        visibility=(),
    ),
    NexusStructure_Basic=device(
        "nicos_ess.devices.datasinks.nexus_structure.NexusStructureJsonFile",
        description="Provides the NeXus structure",
        nexus_config_path="nicos_ess/ymir/nexus/ymir_nexus.json",
        area_det_collector_device="area_detector_collector",
        instrument_name="ymir",
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
        statustopic=["ymir_filewriter", "ess_filewriter_status"],
        unit="",
    ),
    FileWriterControl=device(
        "nicos_ess.devices.datasinks.file_writer.FileWriterControlSink",
        description="Control for the file-writer",
        brokers=configdata("config.KAFKA_BROKERS"),
        pool_topic="ess_filewriter_pool",
        instrument_topic="ymir_filewriter",
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
