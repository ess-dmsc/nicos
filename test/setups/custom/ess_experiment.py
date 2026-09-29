sysconfig = dict(
    experiment="Exp",
)

devices = dict(
    Exp=device(
        "nicos_ess.devices.experiment2.EssExperiment",
        description="experiment object",
        dataroot="test/nicos_ess/test_devices/data",
        sample="Sample",
        cache_filepath="test/nicos_ess/test_devices/data/cached_proposals/cached_proposals_1.json",
    ),
    Sample=device(
        "nicos_ess.devices.sample.EssSample",
        description="The currently used sample",
    ),
)
