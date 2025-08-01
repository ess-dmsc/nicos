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
    """Provides a panel to view hexapod status. Currently a conceptual panel that
    will not properly connect to a hexapod. Emulates hexapod using virtual motors for each
    'direction' the hexapod should be able to move in with set limits per motor"""

    panelName = "Fake Hexapod Controls"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/hexapod.ui"))

        self.client = client
        self.device_panel = parent
        self.setup_connections(client)

        # hiding since it is not currently being used
        self._hideAcceleration()

        # self.setupSliders()

    def setup_connections(self, client):
        # client.cache.connect(self.on_client_cache)
        # client.connected.connect(self.on_client_connected)
        # client.setup.connect(self.on_client_setup)
        # client.disconnected.connect(self.on_client_disconnect)
        return

    @pyqtSlot()
    def on_butStart_clicked(self):
        self.move()

    def on_presetStart_clicked(self):
        presetOption = self.presetOption.currentText()

        if presetOption == "RETRACTED" or "USER_ZERO":
            for cur in (
                self.inpNewTx,
                self.inpNewTy,
                self.inpNewTz,
                self.inpNewRx,
                self.inpNewRy,
                self.inpNewRz,
            ):
                cur.setValue(0.00)
        if presetOption == "MACHINE_ZERO":
            for cur in (
                self.inpNewTx,
                self.inpNewTy,
                self.inpNewTz,
            ):
                cur.setValue(30.00)
        self.move()

    # trying to see if the motors can be moved using the start button
    def move(self):
        return (
            self.client.run(
                "move(%s, %r,%s, %r,%s, %r,%s, %r,%s, %r,%s, %r,)"
                % (
                    "tx",
                    self.inpNewTx.value(),
                    "ty",
                    self.inpNewTy.value(),
                    "tz",
                    self.inpNewTz.value(),
                    "rx",
                    self.inpNewRx.value(),
                    "ry",
                    self.inpNewRy.value(),
                    "rz",
                    self.inpNewRz.value(),
                )
            )
            is not None
        )

    def setupSliders(self):
        # hardcoded to see if it works (for now)
        # hardmin = 0.1
        # hardmax = 2

        # self.tmin.setText(f"{hardmin}")
        # self.rmin.setText(f"{hardmin}")
        # self.amin.setText(f"{hardmin}")

        ##self.tmax.setText(f"{hardmax}")
        # self.rmax.setText(f"{hardmax}")
        # self.amax.setText(f"{hardmax}")

        # only need to convert sliders since they work in whole steps
        self.tSlider.setMinimum(self.convert_spin_and_slide(hardmin, "SLIDER"))
        self.tSlider.setMaximum(self.convert_spin_and_slide(hardmax, "SLIDER"))
        self.tSpinBox.setMinimum(hardmin)
        self.tSpinBox.setMaximum(hardmax)

        self.rSlider.setMinimum(self.convert_spin_and_slide(hardmin, "SLIDER"))
        self.rSlider.setMaximum(self.convert_spin_and_slide(hardmax, "SLIDER"))
        self.rSpinBox.setMinimum(hardmin)
        self.rSpinBox.setMaximum(hardmax)

        self.aSlider.setMinimum(self.convert_spin_and_slide(hardmin, "SLIDER"))
        self.aSlider.setMaximum(self.convert_spin_and_slide(hardmax, "SLIDER"))
        self.aSpinBox.setMinimum(hardmin)
        self.aSpinBox.setMaximum(hardmax)

    # values for sliders must be converted into int from the min and max but need float for real values in spin box
    def on_tSlider_valueChanged(self):
        self.tSpinBox.setValue(
            self.convert_spin_and_slide(self.tSlider.value(), "SPINNER")
        )

    def on_tSpinBox_valueChanged(self):
        self.tSlider.setValue(
            self.convert_spin_and_slide(self.tSpinBox.value(), "SLIDER")
        )

    def on_rSlider_valueChanged(self):
        self.rSpinBox.setValue(
            self.convert_spin_and_slide(self.rSlider.value(), "SPINNER")
        )

    def on_rSpinBox_valueChanged(self):
        self.rSlider.setValue(
            self.convert_spin_and_slide(self.rSpinBox.value(), "SLIDER")
        )

    def on_aSlider_valueChanged(self):
        self.aSpinBox.setValue(
            self.convert_spin_and_slide(self.aSlider.value(), "SPINNER")
        )

    def on_aSpinBox_valueChanged(self):
        self.aSlider.setValue(
            self.convert_spin_and_slide(self.aSpinBox.value(), "SLIDER")
        )

    def convert_spin_and_slide(self, value, type):
        if type == "SLIDER":
            return int(value * 100)
        if type == "SPINNER":
            return float(value / 100)

    def on_applySpeedSettings_clicked(self):
        # self.showError(f"Values taken are
        # {self.translationSpinBox.value()}, {self.rotationSpinBox.value()}, and {self.accelerationSpinBox.value()}")
        self._get_hexapod_info()

    def on_client_connected(self):
        self._get_hexapod_info()

    def on_client_setup(self, setup):
        self._get_hexapod_info()

    def _get_hexapod_info(self):
        devices = self.client.eval("session.devices", {})

        hexapod_info = []

        for dev_name in devices.keys():
            hex_info = {"hexapod": dev_name}
            for param in ["t_speed", "r_speed"]:
                value = self.client.eval(f"{dev_name}.{param}", None)
                if value is None:
                    continue

                hex_info[param] = value

            hexapod_info.append(hex_info)
            data_test = hexapod_info[8]["t_speed"]

        # self.showError(f"{hexapod_info}")
        self.showError(f"{data_test}")

    def _hideAcceleration(self):
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
