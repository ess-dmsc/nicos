description = 'setup for the HTML status monitor'
group = 'special'

_expcolumn = Column(
    Block('Experiment', [
        BlockRow(Field(name='Proposal', key='exp/proposal', width=7),
                 Field(name='Title',    key='exp/title',    width=15,
                       istext=True, maxlen=15),
                 Field(name='Sample',   key='sample/samplename', width=15,
                       istext=True, maxlen=15),
                 Field(name='Remark',   key='exp/remark',   width=30,
                       istext=True, maxlen=30),
                 Field(name='Current status', key='exp/action', width=30,
                       istext=True),
                 Field(name='Last file', key='exp/lastscan')),
        ],
    ),
)


primary = Block('Monochromator', [
    BlockRow(
        Field(dev='wavelength', name='Lambda'),
        Field(dev='cuv', name='Focus v.'),
        Field(dev='cuh', name='Focus h.'),
    ),
    ],
)

sample = Block('Sample stage', [
    BlockRow(
        Field(dev='xtrans', format='%.2f'),
        Field(dev='ytrans', format='%.2f'),
        Field(dev='chi1', format='%.1f'),
        Field(dev='chi2', format='%.1f'),
    ),
    BlockRow(
        Field(dev='gamma',format='%.2f'),
        Field(dev='omega',format='%.2f'),
        Field(dev='liftingctr', name='nu'),
    ),
    ],
)

shutters = Block('Shutters', [
    BlockRow(
        Field(dev='ReactorPower', name='Reactor'),
        Field(dev='Shutter', name='Shutter'),
    ),
    ],
)

collimation = Block('Slits', [
    BlockRow(
        Field(dev='bm',name='Before Mono'),
    ),
    BlockRow(
        Field(dev='bp', name='Before Sample'),
    ),
    ],
)


detector = Block('Detector', [
    BlockRow(
        Field(dev='timer'),
        Field(dev='mon1', format='%d'),
        Field(dev='mon2', format='%d'),
    ),
    BlockRow(
        Field(dev='ctr1', format='%d'),
    ),
    ],
    setups='detector',
)

camera = Block('Camera', [
    BlockRow(
        Field(dev='camtimer', name='timer', format='%.1f'),
        Field(dev='cam_temp', name='temp', format='%.1f'),
        Field(name='Last image', key='exp/lastpoint'),
    ),
    ],
    setups='camera',
)

column1 = Column(primary, sample, detector, camera)

# generic Cryo-stuff
cryos = []
cryosupps = []
cryoplots = []
cryonames = ['cci3he01', 'cci3he02', 'cci3he03', 'cci3he10', 'cci3he11',
             'cci3he12', 'ccidu01', 'ccidu02']
for cryo in cryonames:
    cryos.append(SetupBlock(cryo))
    cryosupps.append(SetupBlock(cryo, 'pressures'))
    cryoplots.append(SetupBlock(cryo, 'plots'))


# generic CCR-stuff
ccrs = []
ccrsupps = []
ccrplots = []
for i in range(10, 22 + 1):
    ccrs.append(
        Block('CCR%d-Pulse tube' % i, [
            BlockRow(
                Field(dev='t_ccr%d_c' % i, name='Coldhead'),
                Field(dev='t_ccr%d_d' % i, name='Regulation'),
                Field(dev='t_ccr%d_b' % i, name='Sample'),
            ),
            BlockRow(
                Field(key='t_ccr%d/setpoint' % i, name='Setpoint'),
                Field(key='t_ccr%d/p' % i, name='P', width=7),
                Field(key='t_ccr%d/i' % i, name='I', width=7),
                Field(key='t_ccr%d/d' % i, name='D', width=6),
            ),
            ],
            setups='ccr%d and not cci3he0*' % i,
        )
    )
    ccrsupps.append(
        Block('CCR%d' % i, [
            BlockRow(
                Field(dev='T_ccr%d_A' % i, name='A'),
                Field(dev='T_ccr%d_B' % i, name='B'),
            ),
            BlockRow(
                Field(dev='T_ccr%d_C' % i, name='C'),
                Field(dev='T_ccr%d_D' % i, name='D'),
            ),
            BlockRow(
                Field(dev='ccr%d_p1' % i, name='P1'),
                Field(dev='ccr%d_p2' % i, name='P2'),
            ),
            BlockRow(
                Field(key='t_ccr%d/setpoint' % i, name='SetP.', width=6),
                Field(key='t_ccr%d/p' % i, name='P', width=4),
                Field(key='t_ccr%d/i' % i, name='I', width=4),
                Field(key='t_ccr%d/d' % i, name='D', width=3),
            ),
            ],
            setups='ccr%d' % i,
        )
    )
    ccrplots.append(
        Block('CCR%d' % i, [
            BlockRow(
                Field(widget='nicos.guisupport.plots.TrendPlot',
                      plotwindow=300, width=25, height=25,
                      devices=['t_ccr%d/setpoint' % i, 't_ccr%d_c' % i,
                               't_ccr%d_d' % i, 't_ccr%d_b' % i],
                      names=['Setpoint', 'Coldhead', 'Regulation', 'Sample'],
                ),
            ),
            ],
            setups='ccr%d' % i,
        )
    )

var1 = Block('Variox', [
    BlockRow(
        Field(dev='T_var1', name='Regulation', max=38),
        Field(dev='T_var1_sample', name='Sample', max=38),
        Field(dev='T_var1_vti', name='VTI',max=7),
    ),
    BlockRow(
        Field(key='T_var1/setpoint', name='Setpoint'),
        Field(key='T_var1/p', name='P', width=7),
        Field(key='T_var1/i', name='I', width=7),
        Field(key='T_var1/d', name='D', width=7),
    ),
    ],
    setups='var1',
)

var1supp1 = Block('Variox - cryoliquids', [
    BlockRow(
        Field(dev='var1_lhe_fill', name='LHe', width=10),
        Field(dev='var1_ln2_fill', name='LN2', width=10),
    ),
    ],
    setups='var1'
)
var1supp2 = Block('Variox - pressures', [
    BlockRow(
        Field(dev='var1_nv', name='N.V.', width=10),
        Field(dev='var1_p', name='p reg.', width=10),
    ),
    BlockRow(
        Field(key='var1_p/status[1]', name='Status', maxlen=6),
    ),
    BlockRow(
        Field(key='var1_p/setpoint', name='p (sp)'),
        Field(key='var1_p/p', name='P', width=6),
        Field(key='var1_p/i', name='I', width=6),
        Field(key='var1_p/d', name='D', width=6),
    ),
    BlockRow(
        Field(dev='var1_piso', name='p (iso)', width=7, unit=''),
        Field(dev='var1_ppump', name='p (pump)', width=7, unit=''),
        Field(dev='var1_psample', name='p (sample)', width=6, unit=''),
    ),
    ],
    setups='var1',
)

ccm8v = SetupBlock('ccm8v', 'short')

column2 = Column(shutters, collimation, ccm8v) + Column(*cryos) + Column(*ccrs) + \
          Column(var1)
column3 = Column(var1supp1, var1supp2) + \
          Column(*cryosupps) + Column(*ccrsupps)

column4 = Column(*cryoplots) + Column(*ccrplots)

devices = dict(
    Monitor = device('nicos.services.monitor.html.Monitor',
        title = 'POLI Status monitor',
        filename = '/control/webroot/index.html',
        interval = 10,
        loglevel = 'info',
        cache = 'phys.poli.frm2',
        prefix = 'nicos/',
        font = 'Luxi Sans',
        valuefont = 'Consolas',
        fontsize = 17,
        layout = [[_expcolumn],
                  [column1, column2, column3],
                  [column4]],
        noexpired = True,
    ),
)
