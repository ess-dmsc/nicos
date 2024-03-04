"""NICOS GUI default configuration."""

main_window = docked(
    tabbed(
        ('Experiment', panel('nicos_ess.gui.panels.exp_panel.ExpPanel')),
        ('Setup',
         panel('nicos.clients.flowui.panels.setup_panel.SetupsPanel')),
        ('  ', panel('nicos_ess.gui.panels.empty.EmptyPanel')),
        (
            'Instrument interaction',
            hsplit(
                vbox(
                    panel(
                        'nicos_ess.gui.panels.cmdbuilder.CommandPanel',
                    ),
                    tabbed(
                        ('Output',
                         panel(
                             'nicos_ess.gui.panels.console.ConsolePanel',
                             hasinput=False)),
                        ('Scan Plot',
                         panel('nicos_ess.gui.panels.scans.ScansPanel')
                         ),
                        ('Detector Image',
                         panel(
                             'nicos.clients.flowui.panels.live.MultiLiveDataPanel'
                         )),
                        ('Script Status',
                         panel(
                             'nicos_ess.gui.panels.status.ScriptStatusPanel',
                             eta=True)),
                    ),
                ),  # vsplit
                panel(
                    'nicos_ess.gui.panels.devices.DevicesPanel',
                    dockpos='right',
                ),
            ),  # hsplit
        ),
        (
            'Scripting',
            panel('nicos_ess.gui.panels.editor.EditorPanel',
                  tools=None),
        ),
        (
            'History',
            panel('nicos_ess.gui.panels.history.HistoryPanel'),
        ),
        (
            'Logs',
            tabbed(
                ('Errors',
                 panel('nicos_ess.gui.panels.errors.ErrorPanel')),
                ('Log files',
                 panel('nicos_ess.gui.panels.logviewer.LogViewerPanel')
                 ),
            ),
        ),
        position='left',
        margins=(0, 0, 0, 0),
        textpadding=(30, 20),
    ),  # tabbed
)  # docked

windows = []

options = {
    'facility': 'ess',
    'mainwindow_class': 'nicos_ess.gui.mainwindow.MainWindow',
}
