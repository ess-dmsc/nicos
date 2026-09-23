from logging import WARNING

from nicos.clients.gui.dialogs.error import ErrorDialog
from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import pyqtSlot
from nicos.protocols.cache import cache_load
from nicos.utils import findResource
from nicos_ess.gui.panels.utils import attach_status_resources


class HexapodPanel(Panel):
    panelName = "Hexapod Controller"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        attach_status_resources(self)
        loadUi(self, findResource("nicos_ess/freia/gui/panels/ui_files/hexapod.ui"))
        self.useicons = bool(options.get("icons", True))

        # Hexapod info
        self.paraminfo = {}
        self.adevs = {}
        self.qtObj = {}
        self.devname = options.get("setups")
        # Hexapod Controller Info

        # Error Handling
        self._exec_reqid = None
        self._error_window = None
        self._control_dialogs = {}
        self.test = self.devname

        client.setup.connect(self.on_client_setup)
        client.connected.connect(self.on_client_connected)
        client.cache.connect(self.on_client_cache)
        client.message.connect(self.on_client_message)
        self.panelLabel.setText(f"{self.devname.capitalize()}")

    def get_hexapod_info(self):
        self.get_hexapod_data()
        self.setup_qt_vars()

    def on_client_setup(self):
        self.get_hexapod_info()

    def on_client_connected(self):
        self.get_hexapod_info()

    def clear(self):
        self.paraminfo.clear()
        self.adevs.clear()
        self.qtObj.clear()

    def on_client_cache(self, data):
        (time, key, op, value) = data
        if "/" not in key:
            return
        devname, pname = key.split("/")

        if devname == self.devname and pname == "value":
            self.update_position_info(cache_load(value))

    def on_client_message(self, message):
        if message[5] != self._exec_reqid or message[2] < WARNING:
            return
        # show warnings and errors emitted by the current command in a window
        msg = f"{message[0]}: {message[3].strip()}"
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
        self._exec_reqid = self.client.run(command)

    def update_position_info(self, values, valtype="curVal"):
        curval = 0
        for axis in self.qtObj:
            if valtype == "newVal":
                self.qtObj[axis][valtype].setValue(round(values[curval], 3))
            elif valtype == "curVal":
                self.qtObj[axis][valtype].setText(f"{round(values[curval], 3):.3f}")
            else:
                raise NotImplementedError(f"valtype {valtype} is not a valid option")
            curval = curval + 1

    def get_hexapod_data(self):
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
            "gmt": {
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
    def on_refresh_pressed(self):
        # Sets the spin boxes to the current axis positions for easier absolute motion control
        # values = self.client.getDeviceParam(self.devname, "value")
        # self.update_position_info(values, "newVal")
        return

    @pyqtSlot()
    def on_butTest_pressed(self):
        class_typ = "nicos_ess.devices.virtual.hexapod.TableHexapod"
        self.test = self.client.getDeviceList(needs_class=class_typ)
        self.showError(f"{self.test}")
        # data = self.mainwindow.expertmode

    # absolute motion using move in GUI
    @pyqtSlot()
    def on_abs_tx_pressed(self):
        return

    @pyqtSlot()
    def on_abs_ty_pressed(self):
        return

    @pyqtSlot()
    def on_abs_tz_pressed(self):
        return

    @pyqtSlot()
    def on_abs_rx_pressed(self):
        return

    @pyqtSlot()
    def on_abs_ry_pressed(self):
        return

    @pyqtSlot()
    def on_abs_rz_pressed(self):
        return

    @pyqtSlot()
    def on_abs_gmt_pressed(self):
        return

    # relative motion using rmove in GUI

    @pyqtSlot()
    def on_relNeg_tx_pressed(self):
        return

    @pyqtSlot()
    def on_relPos_tx_pressed(self):
        return

    @pyqtSlot()
    def on_relNeg_ty_pressed(self):
        return

    @pyqtSlot()
    def on_relPos_ty_pressed(self):
        return

    @pyqtSlot()
    def on_relNeg_tz_pressed(self):
        return

    @pyqtSlot()
    def on_relPos_tz_pressed(self):
        return

    @pyqtSlot()
    def on_relNeg_rx_pressed(self):
        return

    @pyqtSlot()
    def on_relPos_rx_pressed(self):
        return

    @pyqtSlot()
    def on_relNeg_ry_pressed(self):
        return

    @pyqtSlot()
    def on_relPos_ry_pressed(self):
        return

    @pyqtSlot()
    def on_relNeg_rz_pressed(self):
        return

    @pyqtSlot()
    def on_relPos_rz_pressed(self):
        return

    @pyqtSlot()
    def on_relNeg_gmt_pressed(self):
        return

    @pyqtSlot()
    def on_relPos_gmt_pressed(self):
        return
