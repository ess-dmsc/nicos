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
#   Georg Brandl <g.brandl@fz-juelich.de>
#   Christian Felder <c.felder@fz-juelich.de>
#
# *****************************************************************************

"""NICOS GUI single cmdlet command input."""

from os import path

from nicos.clients.flowui.panels import get_icon
from nicos.clients.gui.cmdlets import get_priority_sorted_categories, \
    get_priority_sorted_cmdlets
from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi, modePrompt
from nicos.guisupport.qt import QAction, QApplication, QKeyEvent, QMenu, Qt, \
    QToolButton, pyqtSlot
from nicos.guisupport.utils import setBackgroundColor
from nicos.utils import importString, findResource


class CommandPanel(Panel):
    """Provides a panel where the user can click-and-choose a NICOS command.

    The command can be generated with the help of GUI elements known as
    "cmdlets".

    Options:

    * ``modules`` (default ``[]``) -- list of additional Python modules that
      contain cmdlets and should be loaded.
    * ``add_presets`` (default ``[]``) -- list of tuples consisting of
      additional preset keys and names (e.g. ``[('m', 'monitor counts')]``).
    """

    panelName = 'Command'

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource('nicos_ess/gui/panels/ui_files/cmdbuilder.ui'))

        self.parent_window = parent
        self.options = options
        self.mapping = {}
        self.current_cmdlet = None
        self.expertmode = self.mainwindow.expertmode

        # collect values of all cmdlets that have been added
        # so that the common fields carry over to the next cmdlet
        self.value_collection = {}

        self.commandInput.history = self.cmdhistory
        self.commandInput.completion_callback = self.completeInput
        self.console = None

        client.initstatus.connect(self.on_client_initstatus)
        client.mode.connect(self.on_client_mode)
        client.simresult.connect(self.on_client_simresult)

        modules = options.get('modules', [])
        for module in modules:
            importString(module)  # should register cmdlets

        for cmdlet in get_priority_sorted_cmdlets():
            action = QAction(cmdlet.name, self)

            def callback(on, cmdlet=cmdlet):
                self.selectCmdlet(cmdlet)
            action.triggered.connect(callback)
            self.mapping.setdefault(cmdlet.category, []).append(action)

        for category in get_priority_sorted_categories()[::-1]:
            if category not in self.mapping:
                continue
            toolbtn = QToolButton(self)
            toolbtn.setText(category)
            toolbtn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            menu = QMenu(self)
            menu.addActions(self.mapping[category])
            toolbtn.setMenu(menu)
            self.btnLayout.insertWidget(1, toolbtn)

        self.set_icons()
        if client.isconnected:
            self.on_client_connected()
        else:
            self.on_client_disconnected()
        client.connected.connect(self.on_client_connected)
        client.disconnected.connect(self.on_client_disconnected)

    def postInit(self):
        self.console = self.parent_window.getPanel('Console')
        if self.console:
            self.console.outView.anchorClicked.connect(
                self.on_consoleView_anchorClicked)

    def on_client_connected(self):
        self.setViewOnly(self.client.viewonly)

    def toggle_frame(self):
        self.frame_visible = not self.frame_visible
        self.frame.setVisible(self.frame_visible)
        self.cmdBtn.setText('Hide Cmd' if self.frame_visible else 'New Cmd')
        self.cmdBtn.setIcon(get_icon('remove-24px.svg' if self.frame_visible
                                     else 'add-24px.svg'))

    def on_client_disconnected(self):
        self.setViewOnly(True)

    def set_icons(self):
        self.cmdBtn.setIcon(get_icon('add-24px.svg'))
        self.simBtn.setIcon(get_icon('play_arrow_outline-24px.svg'))
        self.simBtn.hide()
        self.runBtn.setIcon(get_icon('play_arrow-24px.svg'))
        self.frame.hide()

    def setViewOnly(self, viewonly):
        self.inputFrame.setEnabled(not viewonly)
        self.frame.setEnabled(not viewonly)

    def loadSettings(self, settings):
        self.cmdhistory = settings.value('cmdhistory') or []

    def saveSettings(self, settings):
        # only save 100 entries of the history
        cmdhistory = self.commandInput.history[-100:]
        settings.setValue('cmdhistory', cmdhistory)

    def updateStatus(self, status, exception=False):
        self.commandInput.setStatus(status)

    def setCustomStyle(self, font, back):
        self.commandInput.idle_color = back
        self.commandInput.setFont(font)
        setBackgroundColor(self.commandInput, back)

    def getMenus(self):
        return []

    def setExpertMode(self, expert):
        self.expertmode = expert

    def completeInput(self, fullstring, lastword):
        try:
            return self.client.ask('complete', fullstring, lastword,
                                   default=[])
        except Exception:
            return []

    def on_client_initstatus(self, state):
        self.on_client_mode(state['mode'])

    def on_client_mode(self, mode):
        self.label.setText(modePrompt(mode))

    def on_consoleView_anchorClicked(self, url):
        """Called when the user clicks a link in the out view."""
        scheme = url.scheme()
        if scheme == 'exec':
            self.commandInput.setText(url.path())
            self.commandInput.setFocus()

    def clearCmdlet(self):
        self.value_collection.update(self.current_cmdlet.getValues())
        self.current_cmdlet.removeSelf()
        self.current_cmdlet = None

    def selectCmdlet(self, cmdlet):
        if self.current_cmdlet:
            self.clearCmdlet()
        inst = cmdlet(self, self.client, self.options)
        inst.setValues(self.value_collection)
        inst.buttons.upBtn.setVisible(False)
        inst.buttons.downBtn.setVisible(False)
        inst.cmdletRemove.connect(self.clearCmdlet)
        self.frame.layout().insertWidget(0, inst)
        self.current_cmdlet = inst
        inst.valueModified.connect(self.updateCommand)
        self.updateCommand()

    def _generate(self):
        mode = 'python'
        if self.current_cmdlet is None:
            return
        if self.client.eval('session.spMode', False):
            mode = 'simple'
        if not self.current_cmdlet.isValid():
            return
        return self.current_cmdlet.generate(mode).rstrip()

    def updateCommand(self):
        code = self._generate()
        if code is not None:
            self.commandInput.setText(code)
        else:
            self.commandInput.setText('')

    @pyqtSlot()
    def on_simBtn_clicked(self):
        script = self.commandInput.text()
        if not script:
            return
        self.simBtn.setEnabled(False)
        self.client.tell('simulate', '', script, '0')

    def on_client_simresult(self, data):
        self.simBtn.setEnabled(True)

    @pyqtSlot()
    def on_runBtn_clicked(self):
        # Make sure we add the command to the history.
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Enter,
                          Qt.KeyboardModifier.NoModifier)
        QApplication.postEvent(self.commandInput, event)

    def on_commandInput_execRequested(self, script, action):
        if action == 'queue':
            self.client.run(script)
        else:
            self.client.tell('exec', script)
        self.commandInput.selectAll()
        self.commandInput.setFocus()
        self.commandInput.clear()

    @pyqtSlot()
    def on_cmdBtn_clicked(self):
        self.toggle_frame()
