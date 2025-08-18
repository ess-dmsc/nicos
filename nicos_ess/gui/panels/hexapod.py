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
        self.setup_connections(client)

        # hexapod information
        self.devname = ""
        self.devclass = ""
        self.t_unit = ""
        self.r_unit = ""
        self.t_range = ()
        self.r_range = ()

        # daemon request ID of last command executed from this panel
        # (used to display messages from this command)
        self._current_status = "idle"
        self._exec_reqid = None
        self._error_window = None

    # button is also being used to look at device data structures currently
    def on_butStart_pressed(self):
        # self._move()
        self.set_speed_limits()

    def on_butStop_pressed(self):
        self.exec_command(f"stop({self.devname})")

    def _move(self, immediate=False):
        # collect positions from spinboxes and run move command
        # does not pop up error panel if declared command is out of bounds
        # there is probably a better way...
        target = [
            self.newTx.value(),
            self.newTy.value(),
            self.newTz.value(),
            self.newRx.value(),
            self.newRy.value(),
            self.newRz.value(),
        ]

        self.exec_command(f"move({self.devname}, ({target}))")

    def set_speed_limits(self):
        self.paraminfo = self.client.getDeviceParamInfo(
            self.devname
        )  # details of the parameters
        self.pvals = self.client.getDeviceParams(self.devname)
        t_typ = self.paraminfo["t_speed"]["type"]  # location of the limits
        r_typ = self.paraminfo["r_speed"]["type"]
        self.t_unit = self.paraminfo["t_speed"]["unit"]
        self.r_unit = self.paraminfo["r_speed"]["unit"]
        self.t_range = (t_typ.fr, t_typ.to)
        self.r_range = (r_typ.fr, r_typ.to)

        self.tLabel.setText(f"Translation Speed ({self.t_unit})")
        self.tmin.setText(f"{self.t_range[0]}")
        self.tmax.setText(f"{self.t_range[1]}")

        self.rLabel.setText(f"Rotational Speed ({self.r_unit})")
        self.rmin.setText(f"{self.r_range[0]}")
        self.rmax.setText(f"{self.r_range[1]}")
        self.showError(f"{self.pvals}")
        self.setupSliders()

        # self.showError(f"{r_range}: {r_unit}")

    def update_current_pos(self, values):
        self.curTx.setText("%.3f" % values[0])
        self.curTy.setText("%.3f" % values[1])
        self.curTz.setText("%.3f" % values[2])
        self.curRx.setText("%.3f" % values[3])
        self.curRy.setText("%.3f" % values[4])
        self.curRz.setText("%.3f" % values[5])

    def exec_command(self, command):
        self.client.tell("exec", command)

    def setup_connections(self, client):
        client.setup.connect(self.on_client_setup)
        client.cache.connect(self.on_client_cache)
        client.connected.connect(self.on_client_connected)
        client.disconnected.connect(self.on_client_disconnected)

    def on_client_setup(self):
        self._get_hexapod_name(self.devname)
        self._show_controls()

    def on_client_cache(self, data):
        (time, key, op, value) = data
        devname, pname = key.split("/")

        if pname != "value":
            return
        if devname == self.devname:
            fvalue = cache_load(value)
            self.update_current_pos(fvalue)

    def on_client_connected(self):
        self._get_hexapod_name(self.devname)
        self._show_controls()

    def on_client_disconnected(self):
        self.devname == ""
        self._show_controls()

    def on_applySpeedSettings_clicked(self):
        self.exec_command(f"{self.devname}.t_speed = {self.tSpinBox.value()}")
        self.exec_command(f"{self.devname}.r_speed = {self.rSpinBox.value()}")

    # should show controls if hexapod is within selected devices. Otherwise nothing
    # on load check for hexapod data if exists
    def _show_controls(self):
        devices = self.client.eval("session.devices", {})
        for devname in devices:
            if "hexapod" in devices[devname].lower():
                self.panelLabel.setText(f"Hexapod Controls - {self.devname}")
                self.curPos.show()
                self.grpStatus.show()
                self.newPos.show()

                # to add later
                self.grpSpd.show()
                self.presets.show()
                self.set_speed_limits()
                return
            else:
                continue
        self.panelLabel.setText("Hexapod Controls")
        self.curPos.hide()
        self.grpStatus.hide()
        self.newPos.hide()

        # to add later
        self.grpSpd.hide()
        self.presets.hide()

    def _get_hexapod_name(self, devname):  # hardcoded to virtual hexapod
        if devname != "":
            return

        name = self.client.getDeviceList(
            needs_class="nicos_ess.devices.virtual.hexapod.VirtualHexapod"
        )
        if name:
            self.devname = name[0]

    ####### Spinbox and Slider Conversions
    def setupSliders(self):
        # only need to convert sliders since they work in whole steps
        self.tSlider.setMinimum(self._step_convert(self.t_range[0], "SLIDER"))
        self.tSlider.setMaximum(self._step_convert(self.t_range[1], "SLIDER"))
        self.tSpinBox.setMinimum(self.t_range[0])
        self.tSpinBox.setMaximum(self.t_range[1])

        self.rSlider.setMinimum(self._step_convert(self.r_range[0], "SLIDER"))
        self.rSlider.setMaximum(self._step_convert(self.r_range[1], "SLIDER"))
        self.rSpinBox.setMinimum(self.r_range[0])
        self.rSpinBox.setMaximum(self.r_range[1])

        # add inital speed values to the spin boxes as well
        # self.tSpinbox.value(self.)

    # values for sliders must be converted into int from the min and max but need float for real values in spin box
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
