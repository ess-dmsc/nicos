sysconfig = dict(
    experiment="Exp",
    instrument="YMIR",
)

devices = dict(
    Exp=device(
        "nicos_ess.devices.experiment.EssExperiment",
        description="experiment object",
        dataroot="test/nicos_ess/test_devices/data",
        sample="Sample",
        cache_filepath="test/nicos_ess/test_devices/data/cached_proposals/cached_proposals_1.json",
    ),
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
)
