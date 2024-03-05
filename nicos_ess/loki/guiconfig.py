# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   AÜC Hardal <umit.hardal@ess.eu>
#   Matt Clarke <matt.clarke@ess.eu>
#
# *****************************************************************************
"""NICOS GUI LoKI configuration."""

main_window = docked(
    tabbed(
        ('Experiment',
         panel('nicos_ess.gui.panels.exp_panel.ExpPanel', hide_sample=True)),
        ('Instrument Setup',
         panel('nicos_ess.gui.panels.setups.SetupsPanel')),
        ('Sample Configuration',
         panel('nicos_ess.loki.gui.sample_holder_config.LokiSampleHolderPanel')
         ),
        ('  ', panel('nicos_ess.gui.panels.empty.EmptyPanel')),
        (
            'Instrument Interaction',
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
                             'nicos_ess.gui.panels.live_gr.MultiLiveDataPanel'
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
            'Script Builder',
            panel('nicos_ess.loki.gui.scriptbuilder.LokiScriptBuilderPanel',
                  tools=None),
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
                 panel('nicos_ess.gui.panels.logviewer.LogViewerPanel')),
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
