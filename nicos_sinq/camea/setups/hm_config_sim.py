description = 'Histogram memory connector for simulating'

excludes = ['hm_config']

devices = dict(
    hm_connector = device('nicos_sinq.devices.sinqhm.connector.HttpConnector',
        description = "Connector for Histogram Memory Server",
        byteorder = configdata('config.HISTOGRAM_MEMORY_ENDIANESS'),
        baseurl = configdata('config.HISTOGRAM_MEMORY_URL'),
        base64auth = 'c3B5OjAwNw==',
        lowlevel = True
    ),
    hm_b0_ax_x = device('nicos_sinq.devices.sinqhm.configurator.HistogramConfAxis',
        description = 'Tube',
        lowlevel = True,
        length = 104,
        mapping = 'direct',
        label = 'tubes',
    ),
    hm_b0_ax_y = device('nicos_sinq.devices.sinqhm.configurator.HistogramConfAxis',
        description = 'tube pixels',
        lowlevel = True,
        length = 1024,
        mapping = 'direct',
        label = 'pixels',
        unit = '',
    ),
    hm_ax_tof = device('nicos_sinq.devices.sinqhm.configurator.HistogramConfAxis',
        description = 'TOF axis',
        lowlevel = True,
        mapping = 'boundary',
        array = 'tof_array',
        label = 'TOF',
        unit = 'ms'
    ),
    tof_array = device('nicos_sinq.devices.sinqhm.configurator.HistogramConfArray',
        description = 'TOF Array for histogramming',
        lowlevel = True,
        tag = 'tof',
        formatter = '%9d',
        dim = [
            2,
        ],
        data = [0, -1],
    ),
    hm_bank0 = device('nicos_sinq.devices.sinqhm.configurator.HistogramConfBank',
        description = 'HM First Bank',
        lowlevel = True,
        bankid = 0,
        axes = ['hm_b0_ax_x', 'hm_b0_ax_y', 'hm_ax_tof']
    ),
    hm_configurator = device('nicos_sinq.devices.sinqhm.configurator.ConfiguratorBase',
        description = 'Configurator for the histogram memory',
        filler = 'psd',
        mask = '0x0000000',
        active = '0x00000000',
        increment = 1,
        banks = ['hm_bank0'],
        connector = 'hm_connector'
    ),
)