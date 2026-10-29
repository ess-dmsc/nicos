sysconfig = dict(
    experiment="Exp",
    instrument="YMIR",
    datasinks=["conssink"],
)

devices = dict(
    Exp=device(
        "nicos_ess.devices.experiment.EssExperiment",
        description="experiment object",
        dataroot="data",
        sample="Sample",
        cache_filepath="",
    ),
    YMIR=device(
        "nicos.devices.instrument.Instrument",
        description="instrument object",
        instrument="YMIR",
        responsible="Y. Mir <Ymir.Mir@ess.eu>",
    ),
    Sample=device(
        "nicos_ess.devices.sample.EssSample",
        description="The currently used sample",
    ),
    conssink=device(
        "nicos_ess.devices.datasinks.console_scan_sink.ConsoleScanSink",
    ),
    motor=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-10, 10),
        unit="mm",
        speed=0,
    ),
    timer=device(
        "nicos.devices.generic.VirtualTimer",
        visibility=(),
    ),
    det=device(
        "nicos.devices.generic.Detector",
        timers=["timer"],
    ),
)
