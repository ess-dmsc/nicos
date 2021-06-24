description = 'LoKI Sample Environments'

group = 'optional'

devices = dict(
    ThermostatedCellHolder=device('nicos_ess.loki.devices.'
                    'sample_environments.ThermoStatedCellHolder',
                    description='Cell Holder Configuration',
    ),
)
