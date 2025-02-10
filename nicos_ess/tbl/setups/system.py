description = "system setup"

group = "lowlevel"

sysconfig = dict(
    cache="localhost",
    instrument="TBL",
    experiment="Exp",
    datasinks=["conssink", "daemonsink", "liveview"],
)

modules = ["nicos.commands.standard", "nicos_ess.commands"]

devices = dict(
    TBL=device(
        "nicos.devices.instrument.Instrument",
        description="instrument object",
        instrument="TBL",
        responsible="Robin Woracek <robin.woracek@ess.eu>",
        website="https://europeanspallationsource.se/instruments/tbl",
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
    FileWriter=device(
        "nicos_ess.devices.datasinks.file_writer.Filewriter",
        description="Device that controls the filewriter",
        brokers=configdata("config.KAFKA_BROKERS"),
        pool_topic="ess_filewriter_pool",
        instrument_topic="tbl_filewriter",
        statustopic=["tbl_filewriter", "ess_filewriter_status"],
        timeoutinterval=5,
        stoptimeout=5,
        nexus="NexusStructure",
    ),
    liveview=device(
        "nicos.devices.datasinks.LiveViewSink",
    ),
)
