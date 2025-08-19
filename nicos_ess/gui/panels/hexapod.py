from logging import WARNING

from nicos.clients.gui.dialogs.error import ErrorDialog
from nicos.clients.gui.panels import Panel, showPanel
from nicos.clients.gui.utils import ScriptExecQuestion, dialogFromUi, loadUi
from nicos.core import ADMIN
from nicos.core.status import BUSY, DISABLED, ERROR, NOTREACHED, OK, UNKNOWN, WARN
from nicos.guisupport.colors import colors
from nicos.guisupport.qt import (
    pyqtSignal,
    pyqtSlot,
    sip,
)
from nicos.guisupport.typedvalue import ComboWidget, DeviceParamEdit, DeviceValueEdit
from nicos.protocols.cache import OP_TELL, cache_dump, cache_load
from nicos.utils import AttrDict, findResource
from nicos_ess.gui.panels.panel import Panel
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

        self.setup_connections(client)
        self._hideAcceleration()
        self.setup_hexapod()

    def setup_connections(self, client):
        client.setup.connect(self.on_client_setup)
        client.cache.connect(self.on_client_cache)
        client.connected.connect(self.on_client_connected)
        client.disconnected.connect(self.on_client_disconnected)

        client.device.connect(self.on_client_device)

    def setup_hexapod(self):
        self._get_hexapod_name()
        self._show_controls()
        if self.devname:
            self.get_params()
            self.setupSliders()

    def exec_command(self, command):
        self.client.tell("exec", command)

    def on_client_setup(self):
        self.setup_hexapod()

    def on_client_connected(self):
        self.setup_hexapod()

    def on_client_disconnected(self):
        self.setup_hexapod()

    def on_client_device(self, data):
        return

    def on_client_cache(self, data):
        (time, key, op, value) = data
        devname, pname = key.split("/")

        if pname != "value":
            return
        if devname == self.devname:
            fvalue = cache_load(value)
            self.update_current_pos(fvalue)

    def _get_hexapod_name(self):  # hardcoded to virtual hexapod
        name = self.client.getDeviceList(
            needs_class="nicos_ess.devices.virtual.hexapod.VirtualHexapod"
        )
        if name:
            self.devname = name[0]
        else:
            self.devname = ""

    def get_params(self):
        if self.devname == "":
            return

        params = self.client.getDeviceParamInfo(self.devname)  # parameter details
        paramval = self.client.getDeviceParams(self.devname)  # parameter values

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

        # self.showError(f"{self.paraminfo}")

    # create value formatter?
    def update_current_pos(self, values):
        self.curTx.setText("%.3f" % values[0])
        self.curTy.setText("%.3f" % values[1])
        self.curTz.setText("%.3f" % values[2])
        self.curRx.setText("%.3f" % values[3])
        self.curRy.setText("%.3f" % values[4])
        self.curRz.setText("%.3f" % values[5])

    def _show_controls(self):
        if self.devname:
            self.panelLabel.setText(f"{self.devname.capitalize()}")
            self.curPos.show()
            self.grpStatus.show()
            self.newPos.show()
            self.grpSpd.show()

            # to add
            self.presets.show()
        else:
            self.panelLabel.clear()
            self.curPos.hide()
            self.grpStatus.hide()
            self.newPos.hide()
            self.grpSpd.hide()

            # to add
            self.presets.hide()

    # button is also being used to look at device data structures currently
    @pyqtSlot()
    def on_butStart_pressed(self):
        target = [
            self.newTx.value(),
            self.newTy.value(),
            self.newTz.value(),
            self.newRx.value(),
            self.newRy.value(),
            self.newRz.value(),
        ]

        self.exec_command(f"move({self.devname}, ({target}))")

    @pyqtSlot()
    def on_butStop_pressed(self):
        self.exec_command(f"stop({self.devname})")

    @pyqtSlot()
    def on_butPreset_pressed(
        self,
    ):  # used to look at data structures atm. no functionality
        deviceParams = self.client.eval("session.getSetupInfo()", {})
        self.showError(f"{deviceParams['devices']}")

    @pyqtSlot()
    def on_applySpeedSettings_clicked(self):
        self.exec_command(f"{self.devname}.t_speed = {self.tSpinBox.value()}")
        self.exec_command(f"{self.devname}.r_speed = {self.rSpinBox.value()}")

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
