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
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/hexapod.ui"))

        # Hexapod info
        self.devname = ""
        self.paraminfo = {}
        self.adevs = {}
        self.qtObj = {}
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
        self._hide_acceleration()  # unused, so hidden

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
        devname, pname = key.split("/")

        if pname != "value":
            return
        if devname == self.devname:
            fvalue = cache_load(value)
            self.update_current_pos(fvalue)

    def on_client_message(self, message):
        if message[5] != self._exec_reqid or message[2] < WARNING:
            # updates gui if device panel is used
            if "t_speed" in message[3] or "r_speed" in message[3]:
                self.update_ui_sliders()
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
            self.grpSpd.show()
            self._show_added_dof()

            # to add
            self.presets.show()
            self.grpStatus.show()
        else:
            self.panelLabel.clear()
            self.curPos.hide()
            self.newPos.hide()
            self.grpSpd.hide()

            # to add
            self.presets.hide()
            self.grpStatus.hide()

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

        params = self.client.getDeviceParamInfo(self.devname)
        num_adev = len(
            self.client.getDeviceValue(self.devname)
        )  # finds number of attached devices

        # update param dict
        for param in ["t_speed", "r_speed"]:
            sub_param_info = {}
            for units in ["type", "unit"]:
                if units == "type":
                    sub_param_info.update({"min": params[f"{param}"][f"{units}"].fr})
                    sub_param_info.update({"max": params[f"{param}"][f"{units}"].to})

                else:
                    sub_param_info.update({f"{units}": params[f"{param}"][f"{units}"]})

            self.paraminfo.update({f"{param}": sub_param_info})
        self.paraminfo.update({"adevs": num_adev})

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

    def propagate_ui(self):
        for keys in self.qtObj:
            self.qtObj[keys]["curUnit"].setText(f"{self.adevs[keys]['unit']}")
            self.qtObj[keys]["newUnit"].setText(f"{self.adevs[keys]['unit']}")

        self.setup_sliders()
        return

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
        }

        if self.paraminfo["adevs"] == 7:
            self.qtObj.update(
                {
                    "table": {
                        "curVal": self.curTab,
                        "newVal": self.newTab,
                        "curLabel": self.curTabLabel,
                        "curUnit": self.curTabUnit,
                        "newLabel": self.newTabLabel,
                        "newUnit": self.newTabUnit,
                    }
                }
            )

    def _show_added_dof(self):
        name = [
            self.curTabLabel,
            self.curTab,
            self.curTabUnit,
            self.newTabLabel,
            self.newTab,
            self.newTabUnit,
        ]

        if self.paraminfo["adevs"] == 7:
            for label in name:
                label.setVisible(True)
        else:
            for label in name:
                label.setVisible(False)

    def _hide_acceleration(self):
        name = [
            self.aLabel,
            self.amin,
            self.amax,
            self.aSlider,
            self.aSpinBox,
            self.aLine,
        ]

        for label in name:
            label.setVisible(False)

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
    def on_butPreset_pressed(self):
        self.showError(f"{self.adevs}")
        return

    # adding @pyqtSlot() causes this button type to become disabled
    def on_applySpeedSettings_clicked(self):
        self.exec_command(f"{self.devname}.t_speed = {self.tSpinBox.value()}")
        self.exec_command(f"{self.devname}.r_speed = {self.rSpinBox.value()}")

    def setup_sliders(self):
        self.tLabel.setText(f"Translation Speed ({self.paraminfo['t_speed']['unit']})")
        self.tmin.setText(f"{self.paraminfo['t_speed']['min']}")
        self.tmax.setText(f"{self.paraminfo['t_speed']['max']}")

        self.rLabel.setText(f"Rotational Speed ({self.paraminfo['r_speed']['unit']})")
        self.rmin.setText(f"{self.paraminfo['r_speed']['min']}")
        self.rmax.setText(f"{self.paraminfo['r_speed']['max']}")

        # only need to convert sliders since they work in whole steps
        self.tSlider.setMinimum(
            self._step_convert(self.paraminfo["t_speed"]["min"], "SLIDER")
        )
        self.tSlider.setMaximum(
            self._step_convert(self.paraminfo["t_speed"]["max"], "SLIDER")
        )
        self.tSpinBox.setMinimum(self.paraminfo["t_speed"]["min"])
        self.tSpinBox.setMaximum(self.paraminfo["t_speed"]["max"])

        self.rSlider.setMinimum(
            self._step_convert(self.paraminfo["r_speed"]["min"], "SLIDER")
        )
        self.rSlider.setMaximum(
            self._step_convert(self.paraminfo["r_speed"]["max"], "SLIDER")
        )
        self.rSpinBox.setMinimum(self.paraminfo["r_speed"]["min"])
        self.rSpinBox.setMaximum(self.paraminfo["r_speed"]["max"])
        self.update_ui_sliders()

    def update_ui_sliders(self):
        paramval = self.client.getDeviceParams(self.devname)

        self.tSpinBox.setValue(paramval["t_speed"])
        self.rSpinBox.setValue(paramval["r_speed"])
        self.curT.setText(f"[{paramval['t_speed']}]")
        self.curR.setText(f"[{paramval['r_speed']}]")

    def on_tSlider_valueChanged(self):
        self.tSpinBox.setValue(self._step_convert(self.tSlider.value(), "SPINNER"))

    def on_tSpinBox_valueChanged(self):
        self.tSlider.setValue(self._step_convert(self.tSpinBox.value(), "SLIDER"))

    def on_rSlider_valueChanged(self):
        self.rSpinBox.setValue(self._step_convert(self.rSlider.value(), "SPINNER"))

    def on_rSpinBox_valueChanged(self):
        self.rSlider.setValue(self._step_convert(self.rSpinBox.value(), "SLIDER"))

    def _step_convert(self, value, type):
        if type == "SLIDER":
            return int(value * 100)
        if type == "SPINNER":
            return float(value / 100)
