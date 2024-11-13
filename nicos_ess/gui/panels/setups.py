"""NICOS GUI experiment setup window."""

from nicos.clients.gui.panels import Panel
from nicos.clients.gui.panels.setup_panel import AliasWidget
from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import (
    QDialog,
    QDialogButtonBox,
    QListWidgetItem,
    QPushButton,
    Qt,
)
from nicos.utils import findResource


def iterChecked(listwidget):
    """Yield checked items in a QListWidget"""
    for i in range(listwidget.count()):
        item = listwidget.item(i)
        if item.checkState() == Qt.CheckState.Checked:
            yield item


class SetupsPanel(Panel):
    """Provides a dialog to select and load the basic and optional setups."""

    panelName = "Setup selection"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/setups.ui"))
        self.errorLabel.hide()
        self.aliasGroup.hide()
        self._reload_btn = QPushButton("Reload current setup")
        self.finishUi()

        self._aliasWidgets = {}
        self._alias_config = None
        self._setupinfo = {}
        self._loaded = set()
        self._loaded_basic = None
        self._prev_aliases = {}
        self._prev_alias_config = None

        if client.isconnected:
            self.on_client_connected()
        else:
            self.on_client_disconnected()
        client.connected.connect(self.on_client_connected)
        client.setup.connect(self.on_client_connected)
        client.disconnected.connect(self.on_client_disconnected)

    def finishUi(self):
        self.buttonBox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Apply)
        self.buttonBox.addButton(
            self._reload_btn, QDialogButtonBox.ButtonRole.ResetRole
        )

    def on_client_connected(self):
        # fill setups
        self._setupinfo = self.client.eval("session.readSetupInfo()", {})
        all_loaded = self.client.eval("session.loaded_setups", set())
        self._prev_aliases = self.client.eval(
            "{d.name: d.alias for d in session.devices.values() "
            'if "alias" in d.parameters}',
            {},
        )
        self._loaded = set()
        self._loaded_basic = None
        self.basicSetup.clear()
        self.optSetups.clear()
        self.pnpSetups.clear()
        self.errorLabel.hide()
        default_flags = (
            Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
        )
        keep = QListWidgetItem("<keep current>", self.basicSetup)
        if self._setupinfo is not None:
            for name, info in sorted(self._setupinfo.items()):
                if info is None:
                    self.errorLabel.show()
                    continue
                if info["group"] == "basic":
                    QListWidgetItem(name, self.basicSetup)
                    if name in all_loaded:
                        self._loaded_basic = name
                        self._loaded.add(name)
                elif info["group"] == "optional":
                    item = QListWidgetItem(name, self.optSetups)
                    item.setFlags(default_flags)
                    item.setData(Qt.ItemDataRole.UserRole, 0)
                    if name in all_loaded:
                        self._loaded.add(name)
                    item.setCheckState(
                        Qt.CheckState.Checked
                        if name in all_loaded
                        else Qt.CheckState.Unchecked
                    )
                elif info["group"] == "plugplay":
                    item = QListWidgetItem(name, self.pnpSetups)
                    item.setFlags(default_flags)
                    item.setData(Qt.ItemDataRole.UserRole, 1)
                    if name in all_loaded:
                        self._loaded.add(name)
                    item.setCheckState(
                        Qt.CheckState.Checked
                        if name in all_loaded
                        else Qt.CheckState.Unchecked
                    )
                    if name not in all_loaded:
                        item.setHidden(True)

        self.basicSetup.setCurrentItem(keep)
        self._prev_alias_config = self._alias_config
        self.setViewOnly(self.client.viewonly)

    def on_client_disconnected(self):
        self.basicSetup.clear()
        self.optSetups.clear()
        self.pnpSetups.clear()
        self.setViewOnly(True)

    def setViewOnly(self, viewonly):
        for button in self.buttonBox.buttons():
            button.setEnabled(not viewonly)
        self.basicSetup.setEnabled(not viewonly)
        self.optSetups.setEnabled(not viewonly)
        self.pnpSetups.setEnabled(not viewonly)

    def on_basicSetup_currentItemChanged(self, item, old):
        if item and item.text() != "<keep current>":
            self.showSetupInfo(item.text())
        self.updateAliasList()

    def on_basicSetup_itemClicked(self, item):
        if item.text() != "<keep current>":
            self.showSetupInfo(item.text())
        self.updateAliasList()

    def on_optSetups_currentItemChanged(self, item, old):
        if item:
            self.showSetupInfo(item.text())

    def on_optSetups_itemClicked(self, item):
        self.showSetupInfo(item.text())
        self.updateAliasList()

    def on_buttonBox_clicked(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QDialogButtonBox.ButtonRole.ApplyRole:
            self.applyChanges()
        elif role == QDialogButtonBox.ButtonRole.RejectRole:
            self.closeWindow()
        elif role == QDialogButtonBox.ButtonRole.ResetRole:
            if self.client.run("NewSetup()", noqueue=True) is None:
                self.showError("Could not reload setups, a script is running.")
            else:
                self.showInfo("Current setups reloaded.")
                # Close the window only in case of use in a dialog, not in a
                # tabbed window or similiar
                if isinstance(self.parent(), QDialog):
                    self.closeWindow()

    def showSetupInfo(self, setup):
        info = self._setupinfo[str(setup)]
        devs = []
        for devname, devconfig in info["devices"].items():
            if "devlist" in devconfig[1].get("visibility", ("devlist",)):
                devs.append(devname)
        devs = ", ".join(sorted(devs))
        self.setupDescription.setText(
            "<b>%s</b><br/>%s<br/><br/>"
            "Devices: %s<br/>" % (setup, info["description"], devs)
        )

    def toggle_pnp_setup_visibility(self, name, hide):
        for i in range(self.pnpSetups.count()):
            item = self.pnpSetups.item(i)
            if item.text() == name:
                item.setHidden(hide)

    def _calculateSetups(self):
        cur = self.basicSetup.currentItem()
        if cur:
            basic = cur.text()
        else:
            basic = "<keep current>"
        # calculate the new setups
        setups = set()
        new_basic = False
        if basic == "<keep current>":
            if self._loaded_basic:
                setups.add(self._loaded_basic)
        else:
            setups.add(basic)
            new_basic = True
        for item in iterChecked(self.optSetups):
            setups.add(item.text())
        for item in iterChecked(self.pnpSetups):
            setups.add(item.text())
        return setups, new_basic

    def updateAliasList(self):
        setups, _ = self._calculateSetups()
        # get includes as well
        seen = set()

        def add_includes(s):
            if s in seen or s not in self._setupinfo:
                return
            seen.add(s)
            for inc in self._setupinfo[s]["includes"]:
                add_includes(inc)
                setups.add(inc)

        for setup in setups.copy():
            add_includes(setup)
        # now collect alias config
        alias_config = {}
        for setup in setups:
            if "alias_config" in self._setupinfo[setup]:
                aliasconfig = self._setupinfo[setup]["alias_config"]
                for aliasname, targets in aliasconfig.items():
                    for target, prio in targets.items():
                        alias_config.setdefault(aliasname, []).append((target, prio))
        # sort by priority
        for alias in alias_config.values():
            alias.sort(key=lambda x: -x[1])
        # create/update widgets
        layout = self.aliasGroup.layout()
        # only preselect previous aliases if we have the same choices for them
        # as in the beginning
        for aliasname in sorted(alias_config):
            preselect = self._prev_alias_config is None or (
                alias_config.get(aliasname) == self._prev_alias_config.get(aliasname)
            )
            selections = [x[0] for x in alias_config[aliasname]]
            if aliasname in self._aliasWidgets:
                self._aliasWidgets[aliasname].setSelections(
                    selections, preselect and self._prev_aliases.get(aliasname)
                )
            else:
                wid = self._aliasWidgets[aliasname] = AliasWidget(
                    self,
                    aliasname,
                    selections,
                    preselect and self._prev_aliases.get(aliasname),
                )
                layout.addWidget(wid)
        for name, wid in list(self._aliasWidgets.items()):
            if name not in alias_config:
                layout.takeAt(layout.indexOf(wid)).widget().deleteLater()
                del self._aliasWidgets[name]
        if alias_config:
            self.aliasGroup.show()
        else:
            self.aliasGroup.hide()
        self._alias_config = alias_config

    def applyChanges(self):
        setups, new_basic = self._calculateSetups()
        to_add = setups - self._loaded
        to_remove = self._loaded - setups
        if new_basic:
            success = self._load_basic(setups)
        elif to_add or to_remove:
            success = True
            if to_remove:
                success = self._remove_setups(to_remove)
            if to_add and success:
                success = self._add_setups(to_add, noqueue=not to_remove)
        else:
            # No changes, so ignore
            return
        if not success:
            self.showError("Could not load setups, a script is running.")
            return
        for name, wid in self._aliasWidgets.items():
            self.client.run("%s.alias = %r" % (name, wid.getSelection()))
        if to_add or to_remove or self._aliasWidgets:
            self.showInfo("New setups loaded.")

    def _load_basic(self, setups, noqueue=True):
        return self._run_setup_command("NewSetup", setups, noqueue)

    def _remove_setups(self, to_remove, noqueue=True):
        return self._run_setup_command("RemoveSetup", to_remove, noqueue)

    def _add_setups(self, to_add, noqueue=True):
        return self._run_setup_command("AddSetup", to_add, noqueue)

    def _run_setup_command(self, cmd, setups, noqueue):
        cmd_str = f'{cmd}({", ".join(map(repr, setups))})'
        return self.client.run(cmd_str, noqueue=noqueue) is not None
