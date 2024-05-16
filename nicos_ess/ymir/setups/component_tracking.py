description = 'ODIN Component Tracking System'

group = 'optional'

devices = dict(
    component_tracking=device(
        'nicos_ess.odin.devices.component_tracking.ComponentTrackingDevice',
        description='The component tracking system of ODIN',
        brokers=["10.100.1.19:8093"],
        response_topic="ymir_metrology"
    ),
)