from logging import WARNING

from nicos.clients.gui.dialogs.error import ErrorDialog
from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import pyqtSlot
from nicos.protocols.cache import cache_load
from nicos.utils import findResource


class HexapodPanel(Panel):
    paelName = "Hexapod Controller"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/estia/gui/panels/ui_files/hexapod.ui"))

        # Hexapod info
        self.devname = ""
        self.paraminfo = {}
        self.adevs = {}
        self.qtObj = {}
        self.status = options.get("status")
        self.coordSys = options.get("coord")
        # Hexapod Controller Info

        # Error Handling
        self._exec_reqid = None
        self._error_window = None
        self._control_dialogs = {}

        client.setup.connect(self.on_client_setup)
        client.connected.connect(self.on_client_connected)
        client.disconnected.connect(self.on_client_disconnected)
        client.cache.connect(self.on_client_cache)
        client.message.connect(self.on_client_message)

        self.show_controls(False)

    def get_hexapod_info(self):
        self.get_hexapod_name()
        if self.devname:
            self.get_hexapod_data()
            self.setup_qt_vars()
            self.propagate_ui()
            self.show_controls(True)
        else:
            self.clear()

    def on_client_setup(self):
        self.get_hexapod_info()

    def on_client_connected(self):
        self.get_hexapod_info()

    def on_client_disconnected(self):
        self.clear()

    def on_client_cache(self, data):
        (time, key, op, value) = data
        if "/" not in key:
            return
        devname, pname = key.split("/")

        if devname == self.devname and pname == "value":
            self.update_current_pos(cache_load(value))

        # can't seem to find it in cache but is popagated into 'value' param just fine...
        # so grabbing it from there while updating on cache check
        self.update_status_window(self.client.getDeviceParam(self.status, "value"))
        self.update_coord_window(self.client.getDeviceParam(self.coordSys, "value"))

    def on_client_message(self, message):
        if message[5] != self._exec_reqid or message[2] < WARNING:
            return
        # show warnings and errors emitted by the current command in a window
        msg = "%s: %s" % (message[0], message[3].strip())
        if self._error_window is None:

            def reset_errorwindow():
                self._error_window = None

            self._error_window = ErrorDialog(self)
            self._error_window.accepted.connect(reset_errorwindow)
            self._error_window.addMessage(msg)
            self._error_window.show()
        else:
            self._error_window.addMessage(msg)
            self._error_window.activateWindow()

    def exec_command(self, command):
        self.client.tell("exec", command)
        self._exec_reqid = self.client.run(command)

    def clear(self):
        self.devname = ""
        self.paraminfo.clear()
        self.adevs.clear()
        self.qtObj.clear()
        self.show_controls(False)

    def update_current_pos(self, values):
        curval = 0
        for axis in self.qtObj:
            self.qtObj[axis]["curVal"].setText("%.3f" % values[curval])
            curval = curval + 1

    def show_controls(self, visibility):
        if visibility == True:
            self.panelLabel.setText(f"{self.devname.capitalize()}")
            self.curPos.show()
            self.newPos.show()
            self.newPos_2.show()
            self.statusBox.show()
            self.coordBox.show()
            self.butTest.show()
            self.userModes.setTabVisible(1, 0)
        # better way to hide all this using another group box....but will do it later
        else:
            self.panelLabel.clear()
            self.curPos.hide()
            self.newPos.hide()
            self.newPos_2.hide()
            self.statusBox.hide()
            self.coordBox.hide()
            self.butTest.hide()
            self.userModes.setTabVisible(1, 0)

    def get_hexapod_name(self):
        class_typ = "nicos_ess.devices.virtual.hexapod.VirtualHexapod"

        name = self.client.getDeviceList(needs_class=class_typ)
        if name:
            if len(name) > 1:
                self.showError("Error: 2 Hexapods Found. Panel can only control one!")
                self.clear()
                return
            self.devname = name[0]
        else:
            self.clear()

    def get_hexapod_data(self):
        if self.devname == "":
            return

        # update adev dict
        setup = self.client.eval("session.getSetupInfo()", {})
        hexapod_info = {}

        for key in setup:
            if "hexapod" in key:
                if self.devname in setup[key]["devices"]:
                    hexapod_info = setup[key]

        adevs = hexapod_info["devices"][self.devname][1]
        hexapod_info = hexapod_info["devices"]
        adevs.pop("description")
        hexapod_info.pop(self.devname)

        for keys in adevs:
            mini_dict = {}
            mini_dict.update({"devname": adevs[keys]})
            mini_dict.update({"unit": hexapod_info[adevs[keys]][1]["unit"]})

            self.adevs.update({f"{keys}": mini_dict})

    def update_status_window(self, code):
        # A bit messy but works to get some error indication quickly
        error_val = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 50, 63]
        ready_val = [10, 11, 12, 13, 15, 16, 17, 70, 77]
        ok_val = [40, 41, 43, 44, 45, 47, 48, 49, 64, 68, 69, 73]
        not_ref = 42
        if code:
            code = round(code)
            if code in error_val:
                self.hexStatus.setStyleSheet("background-color: lightred")
            elif code in ready_val:
                self.hexStatus.setStyleSheet("background-color: lightgreen")
            elif code in ok_val:
                self.hexStatus.setStyleSheet("background-color: lightblue")
            elif code == not_ref:
                self.hexStatus.setStyleSheet("background-color: lightorange")
            else:
                self.hexStatus.setStyleSheet("background-color: None")
            self.hexStatus.setText(f"{code}")

    def update_coord_window(self, value):
        # sometimes the mapping is odd for awhile, so checking for int or string and
        # setting text accordingly
        if value == "Work" or 0:
            self.coordSyst.setStyleSheet("background-color: lightorange")
            self.coordSyst.setText("Work")
        if value == "Tool" or 1:
            self.coordSyst.setStyleSheet("background-color: lightgreen")
            self.coordSyst.setText("Tool")

    def propagate_ui(self):
        for keys in self.qtObj:
            self.qtObj[keys]["curUnit"].setText(f"{self.adevs[keys]['unit']}")
            self.qtObj[keys]["newUnit"].setText(f"{self.adevs[keys]['unit']}")

    def setup_qt_vars(self):
        self.qtObj = {
            "tx": {
                "curVal": self.curTx,
                "newVal": self.newTx,
                "curLabel": self.curTxLabel,
                "curUnit": self.curTxUnit,
                "newLabel": self.newTxLabel,
                "newUnit": self.newTxUnit,
            },
            "ty": {
                "curVal": self.curTy,
                "newVal": self.newTy,
                "curLabel": self.curTyLabel,
                "curUnit": self.curTyUnit,
                "newLabel": self.newTyLabel,
                "newUnit": self.newTyUnit,
            },
            "tz": {
                "curVal": self.curTz,
                "newVal": self.newTz,
                "curLabel": self.curTzLabel,
                "curUnit": self.curTzUnit,
                "newLabel": self.newTzLabel,
                "newUnit": self.newTzUnit,
            },
            "rx": {
                "curVal": self.curRx,
                "newVal": self.newRx,
                "curLabel": self.curRxLabel,
                "curUnit": self.curRxUnit,
                "newLabel": self.newRxLabel,
                "newUnit": self.newRxUnit,
            },
            "ry": {
                "curVal": self.curRy,
                "newVal": self.newRy,
                "curLabel": self.curRyLabel,
                "curUnit": self.curRyUnit,
                "newLabel": self.newRyLabel,
                "newUnit": self.newRyUnit,
            },
            "rz": {
                "curVal": self.curRz,
                "newVal": self.newRz,
                "curLabel": self.curRzLabel,
                "curUnit": self.curRzUnit,
                "newLabel": self.newRzLabel,
                "newUnit": self.newRzUnit,
            },
            "table": {
                "curVal": self.curTab,
                "newVal": self.newTab,
                "curLabel": self.curTabLabel,
                "curUnit": self.curTabUnit,
                "newLabel": self.newTabLabel,
                "newUnit": self.newTabUnit,
            },
        }

    @pyqtSlot()
    def on_butStart_pressed(self):
        target = []
        for axis in self.qtObj:
            target.append(self.qtObj[axis]["newVal"].value())
        self.exec_command(f"move({self.devname}, ({target}))")

    @pyqtSlot()
    def on_butStop_pressed(self):
        self.exec_command(f"stop({self.devname})")

    @pyqtSlot()
    def on_butTest_pressed(self):
        data = self.mainwindow.expertmode
        self.showError(f"{data}")

    # relative motion using rmove in GUI

    @pyqtSlot()
    def on_relNeg_tx_pressed(self):
        target = -1 * self.relTx.value()
        self.exec_command(f"rmove('{self.adevs['tx']['devname']}', {target})")

    @pyqtSlot()
    def on_relPos_tx_pressed(self):
        target = self.relTx.value()
        self.exec_command(f"rmove('{self.adevs['tx']['devname']}', {target})")

    @pyqtSlot()
    def on_relNeg_ty_pressed(self):
        target = -1 * self.relTy.value()
        self.exec_command(f"rmove('{self.adevs['ty']['devname']}', {target})")

    @pyqtSlot()
    def on_relPos_ty_pressed(self):
        target = self.relTy.value()
        self.exec_command(f"rmove('{self.adevs['ty']['devname']}', {target})")

    @pyqtSlot()
    def on_relNeg_tz_pressed(self):
        target = -1 * self.relTz.value()
        self.exec_command(f"rmove('{self.adevs['tz']['devname']}', {target})")

    @pyqtSlot()
    def on_relPos_tz_pressed(self):
        target = self.relTz.value()
        self.exec_command(f"rmove('{self.adevs['tz']['devname']}', {target})")

    @pyqtSlot()
    def on_relNeg_rx_pressed(self):
        target = -1 * self.relRx.value()
        self.exec_command(f"rmove('{self.adevs['rx']['devname']}', {target})")

    @pyqtSlot()
    def on_relPos_rx_pressed(self):
        target = self.relRx.value()
        self.exec_command(f"rmove('{self.adevs['rx']['devname']}', {target})")

    @pyqtSlot()
    def on_relNeg_ry_pressed(self):
        target = -1 * self.relRy.value()
        self.exec_command(f"rmove('{self.adevs['ry']['devname']}', {target})")

    @pyqtSlot()
    def on_relPos_ry_pressed(self):
        target = self.relRy.value()
        self.exec_command(f"rmove('{self.adevs['ry']['devname']}', {target})")

    @pyqtSlot()
    def on_relNeg_rz_pressed(self):
        target = -1 * self.relRz.value()
        self.exec_command(f"rmove('{self.adevs['rz']['devname']}', {target})")

    @pyqtSlot()
    def on_relPos_rz_pressed(self):
        target = self.relRz.value()
        self.exec_command(f"rmove('{self.adevs['rz']['devname']}', {target})")

    @pyqtSlot()
    def on_relNeg_gmt_pressed(self):
        target = -1 * self.relTab.value()
        self.exec_command(f"rmove('{self.adevs['table']['devname']}', {target})")

    @pyqtSlot()
    def on_relPos_gmt_pressed(self):
        target = self.relTab.value()
        self.exec_command(f"rmove('{self.adevs['table']['devname']}', {target})")
