description = 'HR spectrometer for NURF setup'

devices = dict(
    hr4=device(
        'nicos_ess.devices.epics.spectrometer.OceanInsightSpectrometer',
        description='A Ocean Insights spectrometer',
        pv_root='hr4:',
        pva=True,
        pollinterval=0.5,
        maxage=None,
        monitor=True,
        acquireunits='us',
    ),
    qepro=device(
        'nicos_ess.devices.epics.spectrometer.OceanInsightSpectrometer',
        description='A Ocean Insights spectrometer',
        pv_root='qepro:',
        pva=True,
        pollinterval=0.5,
        maxage=None,
        monitor=True,
        acquireunits='ms',
    ),
)
