description = 'system setup'

group = 'lowlevel'

sysconfig = dict(
    cache='localhost',
    instrument=None,
    experiment='Exp',
    datasinks=['conssink', 'filesink', 'daemonsink', 'liveview', ],
)

modules = ['nicos.commands.standard', 'nicos_ess.commands.epics', 'nicos_ess.ymir.commands.file_writer']

devices = dict(
    Skeleton=device('nicos.devices.instrument.Instrument',
                    description='instrument object',
                    instrument='ymir',
                    responsible='M. Clarke <matt.clarke@ess.eu>',
                    ),

    Sample=device('nicos.devices.sample.Sample',
                  description='The currently used sample',
                  ),

    Exp=device('nicos_ess.devices.experiment.EssExperiment',
               description="The current experiment",
               dataroot='/opt/nicos-data/ymir',
               sample='Sample',
               server_url='https://useroffice-test.esss.lu.se/graphql',
               instrument='YMIR'
               ),

    filesink=device('nicos.devices.datasinks.AsciiScanfileSink',
                    ),

    conssink=device('nicos.devices.datasinks.ConsoleScanSink',
                    ),

    daemonsink=device('nicos.devices.datasinks.DaemonSink',
                      ),

    Space=device('nicos.devices.generic.FreeSpace',
                 description='The amount of free space for storing data',
                 path=None,
                 minfree=5,
                 ),

    liveview=device('nicos.devices.datasinks.LiveViewSink', ),

    FileWriter=device(
        'nicos_ess.devices.datasinks.file_writer.FileWriterStatus',
        description='Status for file-writer',
        brokers=['172.30.242.20:9092'],
        statustopic='UTGARD_writerCommand',
        unit='',
    ),

    FileWriterParameters=device(
        'nicos_ess.devices.datasinks.file_writer.FileWriterParameters',
        description='File-writer parameters',
        brokers=['172.30.242.20:9092'],
        command_topic='UTGARD_writerCommand',
        nexus_config_path='nicos_ess/ymir/commands/nexus_config.json',
        lowlevel=True,
    ),

)
