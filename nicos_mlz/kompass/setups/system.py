description = "system setup"

group = "lowlevel"

sysconfig = dict(
    cache="kompassctrl",
    instrument="Kompass",
    experiment="Exp",
    datasinks=["conssink", "filesink", "daemonsink"],
    notifiers=["email", "smser"],
)

modules = ["nicos.commands.standard"]

includes = [
    "notifiers",
    "guidehall",
]

devices = dict(
    Kompass=device(
        "nicos.devices.tas.TAS",
        description="instrument object",
        instrument="KOMPASS",
        responsible="Dmitry Gorkov <dmitry.gorkov@frm2.tum.de>",
        website="http://www.mlz-garching.de/kompass",
        operators=[
            "Technische Universität München (TUM)",
            "Universität zu Köln",
        ],
        cell="Sample",
        phi="stt",
        psi="sth",
        mono="mono",
        ana="ana",
        alpha="alphastorage",
        scatteringsense=(1, -1, 1),
        axiscoupling=False,
        psi360=False,
    ),
    Sample=device(
        "nicos_mlz.devices.sample.TASSample",
        description="The currently used sample",
    ),
    Exp=device(
        "nicos_mlz.devices.experiment.Experiment",
        description="The currently running experiment",
        dataroot="/data",
        sample="Sample",
        sendmail=True,
        mailsender="kompass@frm2.tum.de",
        managerights=dict(
            enableDirMode=0o775,
            enableFileMode=0o664,
            disableDirMode=0o550,
            disableFileMode=0o440,
            owner="kompassuser",
            group="kompass",
        ),
        elog=True,
        counterfile="counter",
    ),
    alphastorage=device(
        "nicos_mlz.panda.devices.guidefield.AlphaStorage",
        description="Virtual device for handling \\alpha changes",
        abslimits=(-360, 360),
        unit="deg",
        visibility=(),
    ),
    ki=device(
        "nicos.devices.tas.Wavevector",
        description="incoming wavevector, also sets constant-ki mode when moved",
        unit="A-1",
        base="mono",
        tas="Kompass",
        scanmode="CKI",
    ),
    Ei=device(
        "nicos.devices.tas.Energy",
        description="incoming energy, also sets constant-ki mode when moved",
        unit="meV",
        base="mono",
        tas="Kompass",
        scanmode="CKI",
    ),
    lam=device(
        "nicos.devices.tas.Wavelength",
        description="incoming wavelength for diffraction",
        unit="AA",
        base="mono",
        tas="Kompass",
        scanmode="CKI",
    ),
    filesink=device("nicos.devices.datasinks.AsciiScanfileSink"),
    conssink=device("nicos.devices.datasinks.ConsoleScanSink"),
    daemonsink=device("nicos.devices.datasinks.DaemonSink"),
    Space=device(
        "nicos.devices.generic.FreeSpace",
        description="The amount of free space for storing data",
        path=None,
        minfree=5,
    ),
    LogSpace=device(
        "nicos.devices.generic.FreeSpace",
        description="Free space on the log drive",
        path="/control/log",
        visibility=(),
        warnlimits=(0.5, None),
    ),
)
