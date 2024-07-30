# ruff: noqa: F821
description = "system setup"

group = "lowlevel"

sysconfig = dict(
    cache="localhost",
    instrument="NMX",
    experiment="Exp",
    datasinks=["conssink", "liveview", "daemonsink"],
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
        "nicos.devices.datasinks.LiveViewSink",
    ),
    KafkaForwarderStatus=device(
        "nicos_ess.devices.forwarder.EpicsKafkaForwarder",
        description="Monitors the status of the Forwarder",
        statustopic="loki_forwarder_status",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
    SciChat=device(
        "nicos_ess.devices.scichat.ScichatBot",
        description="Sends messages to SciChat",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
)
