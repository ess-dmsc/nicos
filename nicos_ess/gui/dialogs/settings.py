"""NICOS GUI settings window."""

from nicos.clients.base import ConnectionData
from nicos.clients.gui.utils import DlgUtils, dialogFromUi, loadUi
from nicos.guisupport.qt import QDialog, QListWidgetItem, QTreeWidgetItem, pyqtSlot
from nicos.utils import findResource


class SettingsDialog(DlgUtils, QDialog):
    def __init__(self, main):
        QDialog.__init__(self, main)
        DlgUtils.__init__(self, "Settings")
        loadUi(self, findResource("nicos_ess/gui/dialogs/settings.ui"))
        self.main = main
        self.sgroup = main.sgroup

        genitem = QTreeWidgetItem(self.settingsTree, ["General"], -2)
        QTreeWidgetItem(self.settingsTree, ["Connection presets"], -1)
        self.settingsTree.setCurrentItem(genitem)
        self.stacker.setCurrentIndex(0)

        # general page
        self.instrument.setText(main.instrument)
        self.confirmExit.setChecked(main.confirmexit)
        self.warnWhenAdmin.setChecked(main.warnwhenadmin)
        self.showTrayIcon.setChecked(main.showtrayicon)
        self.autoReconnect.setChecked(main.autoreconnect)
        self.autoSaveLayout.setChecked(main.autosavelayout)
        self.allowOutputLineWrap.setChecked(main.allowoutputlinewrap)

        # connection data page
        self.connpresets = main.connpresets
        for setting, cdata in main.connpresets.items():
            QListWidgetItem(
                setting + " (%s:%s)" % (cdata.host, cdata.port), self.settinglist
            ).setData(32, setting)

    def saveSettings(self):
        self.main.instrument = self.instrument.text()
        self.main.confirmexit = self.confirmExit.isChecked()
        self.main.warnwhenadmin = self.warnWhenAdmin.isChecked()
        self.main.showtrayicon = self.showTrayIcon.isChecked()
        self.main.autoreconnect = self.autoReconnect.isChecked()
        self.main.autosavelayout = self.autoSaveLayout.isChecked()
        self.main.allowoutputlinewrap = self.allowOutputLineWrap.isChecked()
        with self.sgroup as settings:
            settings.setValue(
                "connpresets_new",
                {k: v.serialize() for (k, v) in self.connpresets.items()},
            )
            settings.setValue("instrument", self.main.instrument)
            settings.setValue("confirmexit", self.main.confirmexit)
            settings.setValue("warnwhenadmin", self.main.warnwhenadmin)
            settings.setValue("showtrayicon", self.main.showtrayicon)
            settings.setValue("autoreconnect", self.main.autoreconnect)
            settings.setValue("autosavelayout", self.main.autosavelayout)
            settings.setValue("allowoutputlinewrap", self.main.allowoutputlinewrap)
        if self.main.showtrayicon:
            self.main.trayIcon.show()
        else:
            self.main.trayIcon.hide()

    @pyqtSlot()
    def on_saveLayoutBtn_clicked(self):
        self.main.saveWindowLayout()
        for win in self.main.windows.values():
            win.saveWindowLayout()
        self.showInfo("The window layout was saved.")

    @pyqtSlot()
    def on_settingAdd_clicked(self):
        dlg = dialogFromUi(self, "dialogs/settings_conn.ui")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if not dlg.name.text():
            return
        name = dlg.name.text()
        while name in self.connpresets:
            name += "_"
        cdata = ConnectionData(
            dlg.host.text(),
            dlg.port.value(),
            dlg.login.text(),
            None,
            dlg.viewonly.isChecked(),
            dlg.expertmode.isChecked(),
        )
        self.connpresets[name] = cdata
        QListWidgetItem(
            name + " (%s:%s)" % (cdata.host, cdata.port), self.settinglist
        ).setData(32, name)

    @pyqtSlot()
    def on_settingDel_clicked(self):
        item = self.settinglist.currentItem()
        if item is None:
            return
        del self.connpresets[item.data(32)]
        self.settinglist.takeItem(self.settinglist.row(item))

    @pyqtSlot()
    def on_settingEdit_clicked(self):
        item = self.settinglist.currentItem()
        if item is None:
            return
        cdata = self.connpresets[item.data(32)]
        dlg = dialogFromUi(self, "dialogs/settings_conn.ui")
        dlg.name.setText(item.data(32))
        dlg.name.setEnabled(False)
        dlg.host.setText(cdata.host)
        dlg.port.setValue(cdata.port)
        dlg.login.setText(cdata.user)
        dlg.viewonly.setChecked(cdata.viewonly)
        dlg.expertmode.setChecked(cdata.expertmode)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        cdata.host = dlg.host.text()
        cdata.port = dlg.port.value()
        cdata.user = dlg.login.text()
        cdata.viewonly = dlg.viewonly.isChecked()
        cdata.expertmode = dlg.expertmode.isChecked()
        item.setText("%s (%s:%s)" % (dlg.name.text(), cdata.host, cdata.port))

    def on_settingsTree_itemClicked(self, item, column):
        self.on_settingsTree_itemActivated(item, column)

    def on_settingsTree_itemActivated(self, item, column):
        if self.stacker.count() > 3:
            self.stacker.removeWidget(self.stacker.widget(3))
        if item.type() == -2:
            self.stacker.setCurrentIndex(0)
        elif item.type() == -1:
            self.stacker.setCurrentIndex(1)
        elif item.type() == 0:
            self.stacker.setCurrentIndex(2)
