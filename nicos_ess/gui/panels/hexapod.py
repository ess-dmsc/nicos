from logging import WARNING

from nicos.clients.gui.dialogs.error import ErrorDialog
from nicos.clients.gui.panels import Panel, showPanel
from nicos.clients.gui.utils import ScriptExecQuestion, dialogFromUi, loadUi
from nicos.core.status import BUSY, DISABLED, ERROR, NOTREACHED, OK, UNKNOWN, WARN
from nicos.guisupport.colors import colors
from nicos.guisupport.qt import (
    QBrush,
    QByteArray,
    QComboBox,
    QCursor,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFont,
    QIcon,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPalette,
    QPushButton,
    Qt,
    QTreeWidgetItem,
    pyqtSignal,
    pyqtSlot,
    sip,
)
from nicos.guisupport.typedvalue import ComboWidget, DeviceParamEdit, DeviceValueEdit
from nicos.protocols.cache import OP_TELL, cache_dump, cache_load
from nicos.utils import AttrDict, findResource
from nicos_ess.gui.utils import get_icon


class HexapodPanel(Panel):
    """Provides a panel to view a hexapod's status and allows for easier access to it's controls"""

    panelName = "Hexapod Controller"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/hexapod.ui"))
        # hexapod information
        self.devname = ""
        self.paraminfo = {}
        self.qtObj = {}

        self._current_status = "idle"
        self._exec_reqid = None
        self._error_window = None
        self._control_dialogs = {}

        self.setup_connections(client)
        self._hideAcceleration()
        self.setup_hexapod()

    def setup_connections(self, client):
        client.setup.connect(self.on_client_setup)
        client.cache.connect(self.on_client_cache)
        client.connected.connect(self.on_client_connected)
        client.disconnected.connect(self.on_client_disconnected)
        client.message.connect(self.on_client_message)

    def setup_hexapod(self):
        self._get_hexapod_name()
        if self.devname:
            self.get_params()
            self.create_dof_dict()
            self.setupSliders()
        else:
            self.paraminfo.clear()
        self._show_controls()

    def exec_command(self, command, immediate=False):
        self.client.tell("exec", command)
        self._exec_reqid = self.client.run(command)

    def on_client_setup(self):
        self.setup_hexapod()

    def on_client_connected(self):
        self.devname = ""
        self.setup_hexapod()

    def on_client_disconnected(self):
        self.setup_hexapod()
        # self.clear()

    def on_client_message(self, message):
        # show warnings and errors emitted by the current command in a window
        if message[5] != self._exec_reqid or message[2] < WARNING:
            return
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

    def on_client_cache(self, data):
        (time, key, op, value) = data
        devname, pname = key.split("/")

        if pname != "value":
            return
        if devname == self.devname:
            fvalue = cache_load(value)
            self.update_current_pos(fvalue)

    # hardcoded to virtual hexapod atm. Create catch for >1 pod in device setup?
    def _get_hexapod_name(self):
        sixdof = "nicos_ess.devices.virtual.hexapod.VirtualHexapod"
        sevdof = "nicos_ess.devices.virtual.hexapod.TableHexapod"

        name = self.client.getDeviceList(needs_class=sixdof)
        if name:
            if self.client.getDeviceList(needs_class=sevdof):
                self.paraminfo.update({"total_adev": 7})
            else:
                self.paraminfo.update({"total_adev": 6})
            if len(name) > 1:
                self.showError("Error: 2 Hexapods Found. Panel can only control one!")
                self.devname = ""
                self._show_controls()
            self.devname = name[0]
        else:
            self.devname = ""

    def get_params(self):
        if self.devname == "":
            return

        params = self.client.getDeviceParamInfo(self.devname)  # parameter details
        paramval = self.client.getDeviceParams(self.devname)  # parameter values

        # speed params
        for param in ["t_speed", "r_speed"]:
            sub_param_info = {}
            for units in ["type", "unit"]:
                if units == "type":  # split limit range
                    sub_param_info.update({"min": params[f"{param}"][f"{units}"].fr})
                    sub_param_info.update({"max": params[f"{param}"][f"{units}"].to})

                else:
                    sub_param_info.update({f"{units}": params[f"{param}"][f"{units}"]})

            sub_param_info.update({"curvalue": paramval[param]})
            self.paraminfo.update({f"{param}": sub_param_info})

        # find attached devices

    # create value formatter
    def update_current_pos(self, values):
        curval = 0
        for axis in self.qtObj:
            self.qtObj[axis]["curVal"].setText("%.3f" % values[curval])
            curval = curval + 1

    def get_adevs(self):
        # number of attached devices, name and name in setup
        self.showError(f"{self.device_commands}")

    def create_dof_dict(self):  # based on # of devices. qt objects held in dict
        self.qtObj = {
            "tx": {
                "curVal": self.curTx,
                "newVal": self.newTx,
            },
            "ty": {
                "curVal": self.curTy,
                "newVal": self.newTy,
            },
            "tz": {
                "curVal": self.curTz,
                "newVal": self.newTz,
            },
            "rx": {
                "curVal": self.curRx,
                "newVal": self.newRx,
            },
            "ry": {
                "curVal": self.curRy,
                "newVal": self.newRy,
            },
            "rz": {
                "curVal": self.curRz,
                "newVal": self.newRz,
            },
        }

        # There's a better way somewhere...
        if self.paraminfo["total_adev"] == 7:  # add additional position box
            self.qtObj.update(
                {
                    "table": {
                        "curVal": self.curTab,
                        "newVal": self.newTab,
                    }
                }
            )

    # button is also being used to look at device data structures currently
    @pyqtSlot()
    def on_butStart_pressed(self):
        # figure out how to iterate through widgets
        target = []

        for axis in self.qtObj:
            target.append(self.qtObj[axis]["newVal"].value())

        self.exec_command(f"move({self.devname}, ({target}))")

    @pyqtSlot()
    def on_butStop_pressed(self):
        self.exec_command(f"stop({self.devname})", immediate=True)

    @pyqtSlot()
    def on_butPreset_pressed(self):
        # currently not functional
        self.get_adevs()

    def _show_controls(self):
        if self.devname:
            self.panelLabel.setText(f"{self.devname.capitalize()}")
            self.curPos.show()
            self.newPos.show()
            self.grpSpd.show()

            # to add
            self.presets.show()
            self.grpStatus.show()
            self.show_added_dof()

        else:
            self.panelLabel.clear()
            self.curPos.hide()
            self.newPos.hide()
            self.grpSpd.hide()

            # to add
            self.presets.hide()
            self.grpStatus.hide()

    def on_applySpeedSettings_clicked(self):
        self.showError("Apply Settings")
        self.exec_command(
            f"{self.devname}.t_speed = {self.tSpinBox.value()}", immediate=True
        )
        self.exec_command(
            f"{self.devname}.r_speed = {self.rSpinBox.value()}", immediate=True
        )

    # ----------Spinbox and Slider UI Functionality----------#

    def setupSliders(self):
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

        # add inital speed values to the spin boxes as well
        self.tSpinBox.setValue(self.paraminfo["t_speed"]["curvalue"])
        self.rSpinBox.setValue(self.paraminfo["r_speed"]["curvalue"])

    # sliders only work in int steps
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

    def show_added_dof(self):
        name = [
            self.curTabLabel,
            self.curTab,
            self.curTabUnit,
            self.newTabLabel,
            self.newTab,
            self.newTabUnit,
        ]

        if self.paraminfo["total_adev"] == 7:
            for label in name:
                label.setVisible(True)
        else:
            for label in name:
                label.setVisible(False)

    def _hideAcceleration(self):  # available in .ui but not currently used
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
