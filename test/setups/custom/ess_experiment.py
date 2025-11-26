sysconfig = dict(
    experiment="Exp",
)

devices = dict(
    Exp=device(
        "nicos_ess.devices.experiment.EssExperiment",
        description="experiment object",
        dataroot="data",
        sample="Sample",
        cache_filepath="",

    ),
    Sample=device(
        "nicos_ess.devices.sample.EssSample",
        description="The currently used sample",
    ),
)
