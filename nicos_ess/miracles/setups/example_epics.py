description = 'Description of the device type'

devices = dict(
    # An example of associated PVs that can be read and written
    # Just needs the real PV names inserting
    READ_WRITE_1=device(
        'nicos.devices.epics.EpicsAnalogMoveable',
        description='Read and write',
        readpv='EPICS:READ:PV',
        writepv='EPICS:WRITE:PV',
        epicstimeout=3.0,
    ),
    # An example of a value that is only read
    READ_ONLY=device(
        'nicos.devices.epics.EpicsReadable',
        description='Read-only',
        readpv='EPICS:READ:PV',
        lowlevel=True,
        epicstimeout=3.0,
    ),
    # An example of reading a string value
    READ_ONLY_STRING=device(
        'nicos.devices.epics.EpicsStringReadable',
        description='Read-only string',
        readpv='EPICS:READ:STRING:PV',
        epicstimeout=3.0,
    ),
)
