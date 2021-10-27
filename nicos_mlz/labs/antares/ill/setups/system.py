#  -*- coding: utf-8 -*-

description = 'system setup'

sysconfig = dict(
    cache = 'localhost',
    instrument = 'ANTARES',
    experiment = 'Exp',
    datasinks = ['conssink', 'filesink', 'daemonsink'],
    notifiers = [],  # 'email'],
)

modules = ['nicos.commands.basic', 'nicos.commands.standard',
           'nicos_mlz.antares.commands']

includes = ['notifiers']

devices = dict(
    Sample = device('nicos.devices.experiment.Sample',
        description = 'Default Sample',
    ),
    Exp = device('nicos.devices.experiment.ImagingExperiment',
        description = 'Antares Experiment',
        dataroot = 'data/FRM-II',
        sample = 'Sample',
        mailsender = 'antares@frm2.tum.de',
        propprefix = 'p',
        serviceexp = 'service',
        servicescript = '',
        templates = 'templates',
        sendmail = False,
        zipdata = False,
        managerights = dict(
            enableDirMode = 0o775,
            enableFileMode = 0o664,
            disableDirMode = 0o555,
            disableFileMode = 0o444,
        ),
    ),
    ANTARES = device('nicos.devices.instrument.Instrument',
        description = 'Antares Instrument',
        instrument = 'ANTARES',
        responsible = 'Michael Schulz <michael.schulz@frm2.tum.de>',
        doi = 'http://dx.doi.org/10.17815/jlsrf-1-42',
        operators = ['Technische Universität München (TUM)'],
        website = 'http://www.mlz-garching.de/antares',
    ),
    filesink = device('nicos.devices.datasinks.AsciiScanfileSink',
        description = 'Scanfile storing device',
    ),
    conssink = device('nicos.devices.datasinks.ConsoleScanSink',
        description = 'Device handling console output',
    ),
    daemonsink = device('nicos.devices.datasinks.DaemonSink',
        description = 'Data handling inside the daemon',
    ),
    Space = device('nicos.devices.generic.FreeSpace',
        description = 'Free Space in the RootDir',
        path = '/',
        minfree = 1,
    ),
    HomeSpace = device('nicos.devices.generic.FreeSpace',
        description = 'Free Space in the home directory',
        path = '/home/jkrueger',
        minfree = 1,
    ),
    DataSpace = device('nicos.devices.generic.FreeSpace',
        description = 'Free Space on the DataStorage',
        path = 'data',
        minfree = 1,
    ),
    VarSpace = device('nicos.devices.generic.FreeSpace',
        description = 'Free Space on /var',
        path = '/var',
        minfree = 1,
    ),
    LogSpace = device('nicos.devices.generic.FreeSpace',
        description = 'Free space on the log drive',
        path = 'log',
        lowlevel = False,
        warnlimits = (0.5, None),
        minfree = 1,
    ),
)