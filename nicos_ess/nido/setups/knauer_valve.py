description = 'The Knauer Azura valves.'

devices = dict(
    kv_1=device(
        'nicos_ess.loki.devices.knauer_valve.KnauerValve',
        description='.',
        pvroot='SE:SE-KVU-001:',
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    kv_2=device(
        'nicos_ess.loki.devices.knauer_valve.KnauerValve',
        description='.',
        pvroot='SE:SE-KVU-002:',
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),  

)

